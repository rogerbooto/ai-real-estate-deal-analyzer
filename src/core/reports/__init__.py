# src/core/reports/__init__.py
"""
Media reporting package.

This package defines stable, versioned DTOs and helpers for transforming
computer-vision photo insights into human/agent-consumable media reports.
"""

from __future__ import annotations

from .report_models import (
    MediaCoverage,
    MediaItemSummary,
    MediaReport,
    ParkingSummary,
    ReportVersion,
)

__all__ = [
    "ReportVersion",
    "MediaItemSummary",
    "MediaCoverage",
    "ParkingSummary",
    "MediaReport",
]
