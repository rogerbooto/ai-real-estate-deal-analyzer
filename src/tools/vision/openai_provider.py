# src/tools/vision/openai_provider.py
"""
OpenAI Vision Provider (V1.1) — Adds batch adapter

Purpose
-------
Production `VisionProvider` using OpenAI multimodal models. V1.1 adds a simple
`analyze_batch` that currently loops per image (safe, consistent). Future
optimization: pack multiple images into a single request if the SDK + model
support it reliably.

Environment
-----------
OPENAI_API_KEY  : required
AIREAL_VISION_MODEL       : default "gpt-4o-mini"
AIREAL_VISION_TIMEOUT_S   : default "20"
AIREAL_VISION_MAX_RETRIES : default "2"
"""

from __future__ import annotations

import base64
import json
import os
import re
import time
from pathlib import Path

from .provider_base import RawTag, VisionProvider


class OpenAIProvider(VisionProvider):
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set for OpenAIProvider.")
        try:
            from openai import OpenAI  # type: ignore

            self._client = OpenAI(api_key=api_key)
            self._mode = "responses"
        except Exception:
            try:
                import openai  # type: ignore

                openai.api_key = api_key
                self._client = openai
                self._mode = "chat_completions"
            except Exception as e:
                raise RuntimeError("OpenAI SDK not available. Install `openai>=1.0`.") from e

        self._model = os.getenv("AIREAL_VISION_MODEL", "gpt-4o-mini")
        self._timeout_s = float(os.getenv("AIREAL_VISION_TIMEOUT_S", "20"))
        self._max_retries = int(os.getenv("AIREAL_VISION_MAX_RETRIES", "2"))

    # ---------- single ----------
    def analyze(self, path: str) -> list[RawTag]:
        p = Path(path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"Image not found: {path}")
        image_b64 = _read_b64(p)
        prompt = _build_prompt()

        last_err: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                if self._mode == "responses":
                    out = self._call_responses_api(image_b64, prompt)
                else:
                    out = self._call_chat_completions(image_b64, prompt)
                return _parse_provider_json(out)
            except Exception as e:
                last_err = e
                if attempt < self._max_retries:
                    time.sleep(min(0.5 * (attempt + 1), 2.0))
                else:
                    break
        assert last_err is not None
        raise last_err

    # ---------- batch (adapter for now) ----------
    def analyze_batch(self, paths: list[str]) -> list[list[RawTag]]:
        """
        Conservative batch: call analyze() per image. Stable order, no surprises.
        Future: pack multiple images into one request to reduce latency & cost,
        once the SDK contract and model constraints are consistent in prod.
        """
        return [self.analyze(p) for p in paths]

    # ---------- OpenAI calls ----------
    def _call_responses_api(self, image_b64: str, prompt: str) -> str:
        data_url = f"data:image/jpeg;base64,{image_b64}"
        out = self._client.responses.create(  # type: ignore[attr-defined]
            model=self._model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        # CHANGED: use image_url (Responses API expects this)
                        {"type": "input_image", "image_url": data_url},
                    ],
                }
            ],
            # If your SDK complains about 'timeout', you can remove it or use:
            # self._client = self._client.with_options(timeout=self._timeout_s)
            timeout=self._timeout_s,
        )
        # Prefer the SDK's convenience property if available
        txt = getattr(out, "output_text", None)
        if isinstance(txt, str) and txt.strip():
            return txt

        # Fallbacks for older SDKs/structures
        try:
            first_output = out.output[0]  # type: ignore[index]
            if first_output.type == "message":
                return "".join(
                    c.text
                    for c in first_output.content
                    if getattr(c, "type", "") == "output_text"  # type: ignore[attr-defined]
                )
        except Exception:
            pass
        return getattr(out, "text", "") or json.dumps(getattr(out, "output", ""), default=str)

    def _call_chat_completions(self, image_b64: str, prompt: str) -> str:
        data_url = f"data:image/jpeg;base64,{image_b64}"
        if hasattr(self._client, "chat") and hasattr(self._client.chat, "completions"):
            resp = self._client.chat.completions.create(  # type: ignore[attr-defined]
                model=self._model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
                timeout=self._timeout_s,
            )
            return resp.choices[0].message.content or ""  # type: ignore[union-attr]
        if hasattr(self._client, "ChatCompletion"):
            resp = self._client.ChatCompletion.create(  # type: ignore[attr-defined]
                model=self._model,
                messages=[{"role": "user", "content": prompt + f"\n\n[image: {data_url}]"}],
                request_timeout=self._timeout_s,
            )
            return resp["choices"][0]["message"]["content"]
        raise RuntimeError("Unsupported OpenAI SDK mode for chat completions.")


# ---------- helpers ----------
def _read_b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode("ascii")


def _build_prompt() -> str:
    return (
        "You are a computer-vision tagger for real-estate photos.\n"
        "Return ONLY a raw JSON array (no code fences, no markdown, no prose):\n"
        "Each item: {label, category, confidence, evidence, bbox?}.\n"
        "Categories: room_type | feature | condition | issue. Confidence in [0,1].\n"
        "Evidence ≤ 60 chars. bbox = [x_min,y_min,x_max,y_max] pixels if obvious; else omit.\n"
        "Use ONLY labels from the provided ontology. Be conservative; omit if unsure.\n"
    )


def _parse_provider_json(text: str) -> list[RawTag]:
    """
    Tolerant JSON extractor:
      - Strips Markdown code fences (``` or ```json).
      - If extra prose surrounds JSON, extract the first top-level JSON array.
      - Accept either a JSON array or single object (wrap into list).
      - Truncates 'evidence' to 60 chars; keeps bbox if 4 ints.

    NOTE: Ontology filtering happens later in map_raw_tags(); here we only
    build RawTag items if category looks sane.
    """
    if not isinstance(text, str):
        raise ValueError("Provider returned non-string response.")

    s = text.strip()

    # 1) Strip fenced blocks: ```json ... ``` or ``` ... ```
    if s.startswith("```"):
        # remove leading ```lang optional
        s = re.sub(r"^```(?:json)?\s*", "", s, count=1, flags=re.IGNORECASE)
        # remove trailing fence if present
        s = re.sub(r"\s*```$", "", s, count=1)

    # 2) If it's not pure JSON, try to extract the first JSON array/object
    def _try_load(candidate: str):
        return json.loads(candidate)

    loaded = None
    try:
        loaded = _try_load(s)
    except Exception:
        # Try to find the first JSON array
        m = re.search(r"\[\s*{", s, flags=re.DOTALL)
        if m:
            start = m.start()
            # naive bracket matching to find the end of the top-level array
            depth = 0
            end = None
            for i, ch in enumerate(s[start:], start=start):
                if ch == "[":
                    depth += 1
                elif ch == "]":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            if end:
                loaded = _try_load(s[start:end])
        if loaded is None:
            # Try a single top-level object
            m = re.search(r"\{\s*\"", s)
            if m:
                start = m.start()
                # crude object end: last closing brace
                end = s.rfind("}")
                if end != -1 and end > start:
                    loaded = _try_load(s[start : end + 1])

    if loaded is None:
        raise ValueError("Expected a JSON array/object in provider output.")

    # Normalize to list
    if isinstance(loaded, dict):
        items = [loaded]
    elif isinstance(loaded, list):
        items = loaded
    else:
        raise ValueError("Expected a JSON array/object in provider output.")

    out: list[RawTag] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        label = item.get("label")
        category = item.get("category")
        confidence = item.get("confidence")
        evidence = (item.get("evidence") or "")[:60]
        bbox = item.get("bbox")

        # category sanity (ontology strictness happens later)
        if category not in {"room_type", "feature", "condition", "issue"}:
            continue
        try:
            conf_f = float(confidence)
        except Exception:
            continue

        obj: RawTag = {
            "label": label,
            "category": category,
            "confidence": conf_f,
            "evidence": evidence,
        }  # type: ignore[assignment]
        if isinstance(bbox, list) and len(bbox) == 4:
            try:
                obj["bbox"] = [int(x) for x in bbox]
            except Exception:
                pass
        out.append(obj)

    return out
