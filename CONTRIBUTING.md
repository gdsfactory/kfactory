# Contributing to KFactory

Thank you for your interest in contributing to KFactory! This guide covers the essentials for getting started.

## Development Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/gdsfactory/kfactory.git
   cd kfactory
   ```

2. Install dependencies (requires [uv](https://docs.astral.sh/uv/) and Python 3.12+):

   ```bash
   uv sync --extra dev
   ```

3. Install pre-commit hooks:

   ```bash
   uvx pre-commit install
   ```

## Running Tests

   ```bash
   uv run --extra dev just test
   ```

## Pull Requests

- Fill out the PR template: provide a **Summary** (what and why) and a **Test Plan** (how you verified it).
- Keep PRs focused — one logical change per PR.
- Ensure pre-commit hooks and CI pass before requesting review.

## GenAI Policy

AI-assisted contributions (GitHub Copilot, ChatGPT, Claude, etc.) are welcome. If you use generative AI in your contribution, you must:

- **Disclose it** in the PR description — state which parts were AI-generated or AI-assisted.
- **Review all AI-generated code** for correctness, style, and security before submitting.
- **Write or verify tests** for AI-generated code — the contributor is responsible for test coverage.
- **Take ownership** — you are accountable for the contribution as if you wrote it yourself.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
