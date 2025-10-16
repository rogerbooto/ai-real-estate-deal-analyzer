# src/core/media/intelligence.py

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray
from PIL import Image

try:
    _RESAMPLE_BICUBIC = Image.Resampling.BICUBIC  # Pillow >= 9.1
except AttributeError:  # Pillow < 9.1
    _RESAMPLE_BICUBIC = Image.BICUBIC


# --- Public API --------------------------------------------------------------


@dataclass(frozen=True)
class PaletteColor:
    r: int
    g: int
    b: int

    def to_hex(self) -> str:
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"


def load_bounded_thumbnail(path: Path, max_side: int = 512) -> Image.Image:
    img = Image.open(path)
    try:
        from PIL import ImageOps

        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    img = img.convert("RGB")
    img.thumbnail((max_side, max_side), _RESAMPLE_BICUBIC)
    return img


def compute_phash(path: Path, *, size: int = 32, lowfreq: int = 8) -> str:
    """Compute a DCT-based perceptual hash.

    Steps: grayscale -> resize (size x size) -> 2D DCT -> take [0:lowfreq, 0:lowfreq]
    -> binarize against mean (excluding [0,0]) -> return 64-bit hex string.
    """
    img = Image.open(path).convert("L").resize((size, size), _RESAMPLE_BICUBIC)
    a = np.asarray(img, dtype=np.float32)

    # 2D DCT implemented via separable 1D DCT-II using FFT trick
    def dct_1d(x: NDArray[np.float32]) -> NDArray[np.float32]:
        n = x.shape[0]
        # Even-odd reordering
        x2 = np.concatenate([x[::2], x[1::2][::-1]])
        X = np.fft.fft(x2)
        k = np.arange(n)
        factor = np.exp(-1j * math.pi * k / (2 * n))
        return np.real(X[:n] * factor)

    dct_rows = np.apply_along_axis(dct_1d, 1, a)
    dct_full = np.apply_along_axis(dct_1d, 0, dct_rows)

    dct_low = dct_full[:lowfreq, :lowfreq]
    # Exclude the DC coefficient (index 0) when computing threshold
    dct_flat = dct_low.flatten()
    threshold = dct_flat[1:].mean() if dct_flat.size > 1 else 0.0
    bits = (dct_low > threshold).astype(np.uint8)

    # Flatten to 64 bits (lowfreq should be 8)
    bits_flat = bits.flatten()
    # pack into hex string nibble by nibble
    hex_str = []
    for i in range(0, bits_flat.size, 4):
        nibble = 0
        for j in range(4):
            if i + j < bits_flat.size:
                nibble = (nibble << 1) | int(bits_flat[i + j])
            else:
                nibble <<= 1
        hex_str.append(format(nibble, "x"))

    return "".join(hex_str)


def hamming_distance_hex(h1: str, h2: str) -> int:
    """Hamming distance between two same-length hex strings representing bitfields."""
    if len(h1) != len(h2):
        raise ValueError("Hash lengths differ")
    # Convert to integers per hex chunk
    b1 = int(h1, 16)
    b2 = int(h2, 16)
    x = b1 ^ b2
    return x.bit_count()


def compute_quality(path: Path) -> dict[str, float]:
    """Return simple, fast image quality metrics using only Pillow+NumPy.

    - sharpness: variance of Laplacian (implemented via 3x3 kernel)
    - brightness: mean luminance [0..255]
    - contrast: stddev of luminance [0..255]
    """
    img = Image.open(path).convert("L")
    a: NDArray[np.float32] = np.asarray(img, dtype=np.float32)
    # 3x3 Laplacian kernel
    k: NDArray[np.float32] = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)
    # Convolution (valid) via FFT for speed on larger thumbs
    # For small images, direct conv2d is fine
    from numpy.fft import irfft2, rfft2

    pad_h, pad_w = k.shape
    # Use frequency domain convolution on padded arrays
    H, W = a.shape
    ph = H + pad_h - 1
    pw = W + pad_w - 1
    Af = rfft2(a, s=(ph, pw))
    Kf = rfft2(k, s=(ph, pw))
    L = np.real(irfft2(Af * Kf, s=(ph, pw)))
    # center crop back to original size
    sh, sw = (pad_h - 1) // 2, (pad_w - 1) // 2
    L = L[sh : sh + H, sw : sw + W]
    sharpness = float(np.var(L))

    brightness = float(a.mean())
    contrast = float(a.std(ddof=0))

    # Guard against NaNs
    if not np.isfinite(sharpness):
        sharpness = 0.0
    if not np.isfinite(brightness):
        brightness = 0.0
    if not np.isfinite(contrast):
        contrast = 0.0

    return {
        "sharpness": sharpness,
        "brightness": brightness,
        "contrast": contrast,
    }


def extract_palette(path: Path, k: int = 5, *, thumb_side: int = 256, max_iter: int = 15) -> list[PaletteColor]:
    """Return top-k palette colors via lightweight k-means on a small thumbnail.

    No sklearn dependency: uses a simple k-means with k-means++ init.
    Returns k RGB colors.
    """
    img = load_bounded_thumbnail(path, max_side=thumb_side)
    a: NDArray[np.uint8] = np.asarray(img, dtype=np.uint8)
    pixels: NDArray[np.float32] = a.reshape(-1, 3).astype(np.float32)

    # k-means++ initialization
    rng = np.random.default_rng(42)
    centers: NDArray[np.float32] = np.empty((k, 3), dtype=np.float32)
    # first center
    idx0 = rng.integers(0, pixels.shape[0])
    centers[0] = pixels[idx0]
    # remaining centers
    d2 = np.full(pixels.shape[0], np.inf, dtype=np.float32)
    for ci in range(1, k):
        # update distances to nearest center
        diff = pixels[:, None, :] - centers[None, :ci, :]
        dist2 = np.sum(diff * diff, axis=2)
        d2 = np.minimum(d2, dist2.min(axis=1))
        probs = d2 / (d2.sum() + 1e-8)
        idx = rng.choice(pixels.shape[0], p=probs)
        centers[ci] = pixels[idx]

    # Lloyd's iterations
    for _ in range(max_iter):
        diff = pixels[:, None, :] - centers[None, :, :]
        assign = np.argmin(np.sum(diff * diff, axis=2), axis=1)
        new_centers = centers.copy()
        for ci in range(k):
            mask = assign == ci
            if np.any(mask):
                new_centers[ci] = pixels[mask].mean(axis=0)
        if np.allclose(new_centers, centers):
            break
        centers = new_centers

    centers_u8: NDArray[np.uint8] = np.clip(np.rint(centers), 0, 255).astype(np.uint8)
    return [PaletteColor(int(c[0]), int(c[1]), int(c[2])) for c in centers_u8]


# Simple hero ranking ---------------------------------------------------------


def rank_hero(assets: Sequence[MediaAssetLike], signals: dict[str, Any]) -> MediaAssetLike | None:
    """Choose a hero image deterministically based on a score.

    Expected signals structure:
        signals[sha256] = {
            'size': (w, h),
            'area': w*h,
            'is_duplicate': bool,
            'quality': { 'sharpness': float, 'brightness': float, 'contrast': float },
        }

    Score = area_norm * 0.5 + sharpness_norm * 0.4 + contrast_norm * 0.1 - dup_penalty
    Ties are broken by highest area, then lexicographic sha256 for determinism.
    """
    if not assets:
        return None

    # Gather ranges for normalization
    areas, sharps, contrs = [], [], []
    for a in assets:
        s = signals.get(a.sha256, {})
        areas.append(float(s.get("area", 0.0)))
        q = s.get("quality", {})
        sharps.append(float(q.get("sharpness", 0.0)))
        contrs.append(float(q.get("contrast", 0.0)))

    def norm(x: float, xs: Sequence[float]) -> float:
        mn = min(xs) if xs else 0.0
        mx = max(xs) if xs else 1.0

        if mx <= mn:
            return 0.0
        return (x - mn) / (mx - mn)

    best = None
    best_tuple = None

    for a in assets:
        s = signals.get(a.sha256, {})
        area = float(s.get("area", 0.0))
        q = s.get("quality", {})
        sharp = float(q.get("sharpness", 0.0))
        contr = float(q.get("contrast", 0.0))
        score = 0.5 * norm(area, areas) + 0.4 * norm(sharp, sharps) + 0.1 * norm(contr, contrs)
        if s.get("is_duplicate", False):
            score -= 0.25  # penalty for dup cluster
        tie_break = (score, area, a.sha256)
        if best_tuple is None or tie_break > best_tuple:
            best_tuple = tie_break
            best = a
    return best


# Protocol-like minimal interface used by rank_hero; avoids import cycle.
class MediaAssetLike(Protocol):
    sha256: str
    path: Path
    width: int | None
    height: int | None
