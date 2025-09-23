# tests/test_openai_provider_bootstrap.py
"""
OpenAIProvider Bootstrap (No Network)

Purpose
-------
Ensure the provider fails fast and clearly without OPENAI_API_KEY, so callers
(e.g., cv_tagging) can gracefully fall back.
"""

import importlib

import pytest


def test_openai_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Ensure provider import works but instantiation fails
    mod = importlib.import_module("src.tools.vision.openai_provider")
    with pytest.raises(RuntimeError):
        mod.OpenAIProvider()
