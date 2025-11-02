# tests/integration/test_advisor_cli_dir_mode.py

import json
import subprocess
import sys
from pathlib import Path


def test_advisor_cli_dir_mode(tmp_path: Path):
    deal = tmp_path / "dealA"
    (deal / "photos").mkdir(parents=True)
    (deal / "photos" / "p.jpg").write_bytes(b"\xff\xd8\xff")
    (deal / "listing.txt").write_text("3 bed, 2 bath", encoding="utf-8")
    (deal / "finance.json").write_text(
        '{"irr":0.1,"cashflow_monthly":300,"price_per_sqft":200,"market_ppsf":210,"purchase_price":300000}', encoding="utf-8"
    )

    out = tmp_path / "advisor_output.json"
    cmd = [sys.executable, "-m", "src.cli.advisor_cli", "--files", str(deal), "--out", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text())
    assert "ranked" in data and len(data["ranked"]) == 1
