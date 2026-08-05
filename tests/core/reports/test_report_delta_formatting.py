# tests/core/reports/test_report_delta_formatting.py
"""
Formatting rules for the report's delta ("Change") cells.

A delta is not a level: it needs an explicit sign so a reader never has to infer direction from
context, and it must never render a signed zero. Float subtraction of two engine figures routinely
lands at -1e-13; formatted naively that prints "-$0.00" / "-0.00%", which reads as a real (tiny)
loss and is the kind of detail that quietly destroys trust in a financial document.
"""

from __future__ import annotations

import pytest

from src.core.reports.generator import _fmt_delta_currency, _fmt_delta_rate, _fmt_delta_ratio


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (500.0, "+$500.00"),
        (-500.0, "-$500.00"),
        (1234.5, "+$1,234.50"),
        (0.0, "$0.00"),
        (-1e-9, "$0.00"),  # float artifact must not render as a negative
        (0.004, "$0.00"),  # rounds away at 2dp -> unsigned
        (-0.006, "-$0.01"),  # survives rounding -> keeps its sign
    ],
)
def test_delta_currency(value, expected):
    assert _fmt_delta_currency(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.04, "+0.04"),
        (-0.02, "-0.02"),
        (0.0, "0.00"),
        (-1e-12, "0.00"),
    ],
)
def test_delta_ratio(value, expected):
    assert _fmt_delta_ratio(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.0029, "+0.29%"),
        (-0.0252, "-2.52%"),
        (0.0, "0.00%"),
        (-1e-9, "0.00%"),  # would be "-0.00%" without the snap-to-zero rule
    ],
)
def test_delta_rate(value, expected):
    assert _fmt_delta_rate(value) == expected
