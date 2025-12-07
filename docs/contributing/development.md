---
layout: page
title: Development Setup
description: Set up your development environment for contributing to AgentWeave
parent: Contributing
nav_order: 1
---

# Development Setup

This guide will help you set up your local development environment for contributing to AgentWeave.

## Prerequisites

Before you begin, ensure you have the following installed:

### Required

- **Python 3.10 or higher** - [Download Python](https://www.python.org/downloads/)
  ```bash
  python --version  # Should be 3.10+
  ```

- **Git** - [Install Git](https://git-scm.com/downloads)
  ```bash
  git --version
  ```

- **Docker** - [Install Docker](https://docs.docker.com/get-docker/)
  ```bash
  docker --version
  docker compose --version
  ```

### Optional but Recommended

- **Docker Compose** - For running SPIRE and OPA infrastructure
- **kubectl** - For testing Kubernetes deployments
- **make** - For using the project Makefile
- **jq** - For JSON parsing in scripts

## Fork and Clone the Repository

### 1. Fork the Repository

Visit [https://github.com/aj-geddes/agentweave](https://github.com/aj-geddes/agentweave) and click the "Fork" button to create your own fork.

### 2. Clone Your Fork

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/agentweave.git
cd agentweave

# Add upstream remote
git remote add upstream https://github.com/aj-geddes/agentweave.git

# Verify remotes
git remote -v
```

### 3. Create a Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create a feature branch
git checkout -b feature/your-feature-name
```

Use descriptive branch names:
- `feature/add-custom-transport` - New features
- `fix/spire-connection-timeout` - Bug fixes
- `docs/improve-quickstart` - Documentation
- `refactor/simplify-context` - Code refactoring

## Set Up Virtual Environment

We recommend using a virtual environment to isolate dependencies:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Verify activation
which python  # Should point to venv/bin/python
```

## Install Dependencies

### Install Development Dependencies

```bash
# Install the package in editable mode with dev extras
pip install -e ".[dev]"

# This installs:
# - Core dependencies (grpcio, cryptography, etc.)
# - Development dependencies (pytest, black, mypy, etc.)
# - Documentation dependencies (mkdocs, etc.)
```

The `dev` extras include:

```python
# From setup.py or pyproject.toml
[dev]
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-asyncio>=0.21.0
pytest-timeout>=2.1.0
black>=23.7.0
isort>=5.12.0
mypy>=1.5.0
flake8>=6.1.0
pylint>=2.17.0
pre-commit>=3.3.0
```

### Verify Installation

```bash
# Verify AgentWeave is installed
python -c "import hvs_agent; print(hvs_agent.__version__)"

# Verify dev tools are available
black --version
mypy --version
pytest --version
```

## Configure Pre-commit Hooks

Pre-commit hooks automatically check your code before each commit:

```bash
# Install pre-commit hooks
pre-commit install

# Test the hooks
pre-commit run --all-files
```

Our pre-commit configuration (`.pre-commit-config.yaml`) runs:
- **black** - Code formatting
- **isort** - Import sorting
- **flake8** - Linting
- **mypy** - Type checking
- **trailing whitespace** - Remove trailing spaces
- **end of file** - Ensure newline at end

## Running Tests

### Run All Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=hvs_agent --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Run Specific Tests

```bash
# Run tests in a specific file
pytest tests/test_agent.py

# Run tests matching a pattern
pytest -k "test_identity"

# Run with verbose output
pytest -v

# Run and stop at first failure
pytest -x
```

### Run Integration Tests

Integration tests require Docker to run SPIRE and OPA:

```bash
# Start infrastructure
docker compose -f tests/docker-compose.test.yaml up -d

# Run integration tests
pytest --run-integration

# Stop infrastructure
docker compose -f tests/docker-compose.test.yaml down
```

### Test Configuration

Create a `pytest.ini` or use our existing configuration:

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --strict-markers
    --tb=short
    --cov-report=term-missing
markers =
    unit: Unit tests
    integration: Integration tests requiring infrastructure
    slow: Slow tests
asyncio_mode = auto
```

## Code Style and Linting

We use several tools to maintain code quality:

### Black (Code Formatting)

Black formats code automatically:

```bash
# Format all files
black .

# Check formatting without making changes
black --check .

# Format a specific file
black hvs_agent/agent.py
```

Configuration in `pyproject.toml`:
```toml
[tool.black]
line-length = 100
target-version = ['py310']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''
```

### isort (Import Sorting)

Isort organizes imports:

```bash
# Sort imports
isort .

# Check without making changes
isort --check-only .
```

Configuration in `pyproject.toml`:
```toml
[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
```

### mypy (Type Checking)

mypy checks type hints:

```bash
# Run type checking
mypy hvs_agent

# Check a specific file
mypy hvs_agent/agent.py
```

Configuration in `pyproject.toml`:
```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
strict_equality = true
```

### flake8 (Linting)

flake8 checks code style:

```bash
# Run linting
flake8 hvs_agent tests

# With specific settings
flake8 --max-line-length=100 --extend-ignore=E203,W503 hvs_agent
```

### Run All Checks

```bash
# Run all code quality checks
make lint

# Or manually:
black --check .
isort --check-only .
mypy hvs_agent
flake8 hvs_agent tests
```

## Running the Documentation Locally

AgentWeave documentation is built with Jekyll:

### Install Jekyll

```bash
# Install Ruby (if not already installed)
# On macOS:
brew install ruby

# On Ubuntu:
sudo apt-get install ruby-full build-essential zlib1g-dev

# Navigate to docs directory
cd docs

# Install Jekyll and dependencies
bundle install
```

### Build and Serve Documentation

```bash
# Serve documentation locally
bundle exec jekyll serve

# With live reload
bundle exec jekyll serve --livereload

# On a specific port
bundle exec jekyll serve --port 4001
```

Visit [http://localhost:4000/agentweave/](http://localhost:4000/agentweave/) to view the documentation.

### Build Static Site

```bash
# Build static HTML
bundle exec jekyll build

# Output is in _site/ directory
```

## Making Changes

### 1. Write Your Code

Follow these guidelines:
- **Write clear, readable code** - Use descriptive variable names
- **Add docstrings** - Document all public functions and classes
- **Include type hints** - Use Python type annotations
- **Handle errors gracefully** - Catch and handle exceptions appropriately
- **Write tests** - Add tests for new functionality

### 2. Write Tests

Every new feature or bug fix should include tests:

```python
# tests/test_my_feature.py
import pytest
from hvs_agent import SecureAgent

class TestMyFeature:
    """Test suite for my new feature."""

    def test_basic_functionality(self):
        """Test that basic functionality works."""
        # Arrange
        agent = SecureAgent(config={...})

        # Act
        result = agent.my_new_method()

        # Assert
        assert result == expected_value

    @pytest.mark.asyncio
    async def test_async_functionality(self):
        """Test async functionality."""
        agent = SecureAgent(config={...})
        result = await agent.async_method()
        assert result is not None
```

### 3. Update Documentation

Update relevant documentation:
- **API docs** - Add/update docstrings
- **User guide** - Update guides if behavior changes
- **Examples** - Add example code if appropriate
- **Changelog** - Add entry to `CHANGELOG.md`

### 4. Run Tests and Linting

Before committing:

```bash
# Run all checks
make test
make lint

# Or manually:
pytest
black .
isort .
mypy hvs_agent
flake8 hvs_agent tests
```

## Submitting Pull Requests

### Before Submitting

Ensure your PR meets these requirements:

- [ ] All tests pass (`pytest`)
- [ ] Code is formatted (`black`, `isort`)
- [ ] Type checking passes (`mypy`)
- [ ] Linting passes (`flake8`)
- [ ] Documentation is updated
- [ ] Changelog is updated
- [ ] Commits are descriptive and atomic
- [ ] Branch is up to date with main

### PR Checklist

Use this template for your PR description:

```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Documentation
- [ ] Docstrings updated
- [ ] User guide updated
- [ ] Examples updated
- [ ] Changelog updated

## Related Issues
Closes #123
Related to #456
```

### Submit Your PR

```bash
# Push your branch
git push origin feature/your-feature-name

# Go to GitHub and create a pull request
# Fill out the PR template
# Request review from maintainers
```

## Review Process

### What to Expect

1. **Automated checks** - CI/CD will run tests and linting
2. **Maintainer review** - A maintainer will review your code
3. **Feedback** - You may receive requests for changes
4. **Iteration** - Make requested changes and push updates
5. **Approval** - Once approved, a maintainer will merge your PR

### Responding to Feedback

- **Be responsive** - Reply to comments and questions
- **Be open to suggestions** - Maintainers want to help improve your code
- **Ask questions** - If feedback is unclear, ask for clarification
- **Update your PR** - Push commits to address feedback

### After Merge

Once your PR is merged:
- Your changes will be included in the next release
- You'll be credited in the release notes
- Your name will be added to CONTRIBUTORS.md

## Development Tips

### Use the Makefile

We provide a Makefile for common tasks:

```bash
# Run tests
make test

# Run linting
make lint

# Format code
make format

# Build package
make build

# Clean build artifacts
make clean

# Start dev infrastructure
make infra-up

# Stop dev infrastructure
make infra-down
```

### Environment Variables

Set these for development:

```bash
# .env file
SPIFFE_ENDPOINT_SOCKET=/tmp/spire-agent/public/api.sock
OPA_URL=http://localhost:8181
LOG_LEVEL=DEBUG
PYTHONPATH=.
```

### Debugging

Use these techniques for debugging:

```python
# Add debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug("Debug message")

# Use pdb for interactive debugging
import pdb; pdb.set_trace()

# Use pytest with pdb
pytest --pdb  # Drop into debugger on failure
pytest -x --pdb  # Stop at first failure and debug
```

### Working with SPIRE and OPA

Start local infrastructure for testing:

```bash
# Start SPIRE and OPA
docker compose up -d spire-server spire-agent opa

# Check status
docker compose ps

# View logs
docker compose logs -f spire-agent

# Register a workload
docker compose exec spire-server \
  /opt/spire/bin/spire-server entry create \
  -spiffeID spiffe://example.org/test-agent \
  -parentID spiffe://example.org/spire/agent/x509pop/$(hostname) \
  -selector unix:uid:$(id -u)

# Stop infrastructure
docker compose down
```

## Getting Help

If you need help:

- **Check the docs** - [Full documentation](https://aj-geddes.github.io/agentweave/)
- **Search issues** - [GitHub Issues](https://github.com/aj-geddes/agentweave/issues)
- **Ask in discussions** - [GitHub Discussions](https://github.com/aj-geddes/agentweave/discussions)
- **Contact maintainers** - maintainers@agentweave.io

## Additional Resources

- [Contributing Guide](index.md)
- [Code of Conduct](code-of-conduct.md)
- [Changelog](../changelog.md)
- [Product Specification](../../spec.md)
- [GitHub Repository](https://github.com/aj-geddes/agentweave)

---

**Ready to contribute?** Pick an issue and start coding! We're excited to see what you'll build.
