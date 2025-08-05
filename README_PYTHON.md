# Python Development

## Environment setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Install project and development dependencies:
   ```bash
   pip install -e '.[dev]'
   ```

## Using pre-commit

Install the git hooks and run them locally before committing:

```bash
pre-commit install
pre-commit run --files <file> [<file> ...]
```

To check the entire repository, use:

```bash
pre-commit run --all-files
```

## Running tests

Execute the test suite with pytest:

```bash
pytest
```
