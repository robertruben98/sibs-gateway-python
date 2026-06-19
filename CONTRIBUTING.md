# Contributing to PySIBS

Thanks for your interest in improving PySIBS! Contributions of all kinds are welcome.

## Development setup

```bash
git clone https://github.com/robertruben98/pysibs.git
cd pysibs
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Quality gates

Every change must pass the same checks CI runs:

```bash
ruff check .
python -m mypy pysibs
pytest --cov=pysibs
python -m build
twine check dist/*
```

A change is **done** only when:

- the code is implemented and typed,
- unit tests are added (coverage must stay ≥ 80%),
- `ruff` and `mypy` are clean,
- documentation is updated,
- the public API is not broken without a version bump,
- no secrets or real card data are committed.

## Testing rules

- Unit tests must **never** call a real SIBS environment — mock HTTP with `respx`.
- Integration tests live under `tests/integration/`, are marked
  `@pytest.mark.integration`, and are disabled by default. Run them with
  `pytest -m integration` and real sandbox credentials in the environment.

## Conventions

- Money is always `Decimal`; never accept `float`.
- Never log credentials or `Authorization` headers.
- Don't invent SIBS endpoints, fields or headers. If something is unclear in the
  official docs, keep the interface flexible, document the assumption with a `NOTE`,
  and make sure `raw_response`/`raw_payload` stays available.

## Pull requests

Keep PRs focused, describe the change, and reference any related issue. Update
`CHANGELOG.md` under `[Unreleased]`.
