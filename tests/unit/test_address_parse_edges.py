# tests/unit/test_address_parse_edges.py
from src.core.normalize.address import parse_address


def test_parse_address_handles_none_and_garbage():
    assert parse_address(None) is None
    assert parse_address("???") is None
    out = parse_address("123 Main St, Springfield, IL 62704")
    assert out is not None and out.city == "Springfield"
