# Contributing to The AI Real Estate Deal Analyzer

First off, thank you for your interest in contributing! 🎉
This project is intended as an **open research and educational project**. Contributions that improve the clarity, correctness, or usability of the code and documentation are always welcome.

---

## Development Setup

1. Clone the repo:

   ```bash
   git clone https://github.com/<your-username>/ai-real-estate-deal-analyzer.git
   cd ai-real-estate-deal-analyzer
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux/Mac
   .venv\Scripts\activate      # Windows
   ```

3. Install dependencies (including dev tools):

   For the exact, hash-pinned versions CI installs (recommended):

   ```bash
   pip install -r requirements-dev.lock
   ```

   Or resolve the loose ranges yourself:

   ```bash
   pip install -r requirements.txt -r requirements-dev.txt
   ```

   > Note: `pip install -e .` is supported and installs the console scripts (`ingest-listing`, `deal-report`, `deal-advisor`). Install one of the sets above first, then `pip install -e .` for the entry points.

   If you change `requirements.txt` or `requirements-dev.txt`, regenerate **both** lockfiles so CI
   (which installs from `requirements-dev.lock`, not the loose ranges) picks up the change — requires
   [`uv`](https://github.com/astral-sh/uv):

   ```bash
   # runtime only — what someone needs to just run the tool
   uv pip compile requirements.txt \
     --output-file requirements.lock --python-version 3.10 --generate-hashes

   # runtime + dev tooling — this is the one CI installs
   uv pip compile requirements.txt requirements-dev.txt \
     --output-file requirements-dev.lock --python-version 3.10 --generate-hashes
   ```

   Regenerating only one leaves the two disagreeing about a shared package, which is the same
   split-brain the lockfiles exist to prevent.

4. Run the test suite:

   ```bash
   pytest -q
   ```

   All tests must pass before submitting a pull request.

---

## Coding Standards

* Follow **PEP8** conventions.

* We use **ruff** for linting and formatting. Run:

  ```bash
  ruff check .
  ruff format .
  ```

* Type hints are required (`mypy` is used in CI).

* Write tests for new features or bug fixes.

* Keep functions small and opinionated — one responsibility per function.

---

## Commit Messages

Use clear, conventional commits:

* `feat:` for new features
* `fix:` for bug fixes
* `test:` for adding/updating tests
* `docs:` for documentation changes
* `refactor:` for non-breaking code cleanup

Example:

```text
feat(financial_model): add mortgage insurance integration
```

---

## Pull Requests

* Fork the repo and create a feature branch.
* Ensure tests and linting pass locally before pushing.
* Provide a clear description of your change and motivation.
* PRs should remain focused (avoid bundling unrelated changes).

---

## License & Attribution

This project is released under the **Research & Education License** (see `LICENSE.md`; commercial terms are in `LICENSE-commercial.md`).

* Free to use for **personal, academic, and research purposes**.
* Commercial/business use requires a separate **commercial license**.
* All users must provide attribution to **Roger Booto Tokime** as the original author.

Please respect these terms when contributing.

---

_Last reconciled: 2026-08-19 against main @ 8ed9397 (added `requirements.lock` as the recommended, CI-matching install path and the `uv pip compile` regeneration command; corrected the `LICENSE` filename reference to `LICENSE.md`). Earlier note: 2026-07-23 against main @ e4716df._
