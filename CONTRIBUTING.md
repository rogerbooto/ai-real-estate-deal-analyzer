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

   ```bash
   pip install -e .[dev]
   ```

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

This project is released under the **Research & Education License** (see `LICENSE`).

* Free to use for **personal, academic, and research purposes**.
* Commercial/business use requires a separate **commercial license**.
* All users must provide attribution to **Roger Booto Tokime** as the original author.

Please respect these terms when contributing.