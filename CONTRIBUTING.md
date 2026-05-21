# Contributing to CSC Bicol Job Scraper

Thank you for your interest in improving the CSC Bicol Job Scraper! We welcome contributions to make this tool better for all government job seekers.

## Development Setup

1. Fork the repository and clone it to your local machine.
2. Create a new virtual environment: `python -m venv venv`
3. Activate the environment and install dependencies: `pip install -r requirements.txt`
4. Install testing dependencies: `pip install pytest pytest-cov responses`

## Branching Strategy

We follow a simple branch-PR-merge workflow:
- `main` is the stable production branch.
- For new features, create a branch named `feat/your-feature-name`.
- For bug fixes, use `fix/your-bug-fix`.
- For documentation, use `docs/your-docs-update`.

## Testing

Before submitting a Pull Request, please ensure all tests pass:

```bash
pytest tests/ -v
```

To view code coverage:
```bash
pytest tests/ --cov=src
```

## Pull Request Guidelines

1. **Keep it focused**: Each PR should address a single feature or bug.
2. **Update Documentation**: If you add new configuration options, update `config.yaml` and `README.md`.
3. **Write Tests**: Include tests for your new feature or reproduce the bug you are fixing in a test.
4. **Descriptive Title**: Use conventional commits format for your PR title (e.g., `feat: add email notifications`).

## Code Style

- We follow PEP 8 guidelines.
- Use type hints (`def func(arg: int) -> str:`) for all new functions.
- Add docstrings to all modules, classes, and public functions.
