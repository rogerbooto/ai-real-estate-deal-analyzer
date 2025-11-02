# tests/imports/test_ingest_alias.py


def test_run_ingest_importable():
    from src.core.ingest import run_ingest  # noqa: F401

    assert callable(run_ingest)
