---
layout: page
title: Contributing
description: Learn how to contribute to the AgentWeave SDK project
nav_order: 10
has_children: true
---

# Contributing to AgentWeave

Thank you for your interest in contributing to AgentWeave! We're excited to have you join our community of developers building secure, cross-cloud AI agents.

AgentWeave is an open-source project, and we welcome contributions of all kinds - from bug reports and documentation improvements to new features and code contributions.

## Ways to Contribute

### Report Bugs

Found a bug? Help us improve AgentWeave by reporting it:

1. **Search existing issues** - Check if the bug has already been reported at [GitHub Issues](https://github.com/aj-geddes/agentweave/issues)
2. **Create a detailed report** - Include:
   - Clear description of the bug
   - Steps to reproduce
   - Expected vs. actual behavior
   - Your environment (OS, Python version, AgentWeave version)
   - Relevant logs or error messages
3. **Use the bug report template** - Follow the issue template for consistency

**Example of a good bug report:**
```
Title: SecureAgent fails to start with SPIRE connection timeout

Environment:
- OS: Ubuntu 22.04
- Python: 3.11.5
- AgentWeave: 1.0.0
- SPIRE: 1.8.0

Description:
SecureAgent initialization fails with "Connection timeout" when SPIRE server
is configured with custom socket path.

Steps to reproduce:
1. Configure SPIRE with socket_path: /custom/path/agent.sock
2. Set SPIFFE_ENDPOINT_SOCKET=/custom/path/agent.sock
3. Run agent with: hvs-agent serve config.yaml

Error:
SPIFFEConnectionError: Connection timeout after 5.0s

Expected: Agent should connect to SPIRE using custom socket path
Actual: Agent times out and fails to start
```

### Request Features

Have an idea for a new feature or enhancement?

1. **Check existing requests** - Search [GitHub Issues](https://github.com/aj-geddes/agentweave/issues) for similar requests
2. **Describe your use case** - Explain the problem you're trying to solve
3. **Propose a solution** - Share your thoughts on how it might work
4. **Consider alternatives** - Are there other ways to achieve the same goal?

We love hearing about how you're using AgentWeave and what would make it better!

### Improve Documentation

Documentation improvements are always welcome:

- **Fix typos or errors** - Even small fixes help!
- **Clarify confusing sections** - If something wasn't clear to you, it might confuse others
- **Add examples** - Real-world examples help developers understand concepts
- **Write tutorials** - Share your expertise with the community
- **Improve API docs** - Add or enhance docstrings in the code

See our [Development Guide](development.md) for how to build and test documentation locally.

### Contribute Code

Ready to dive into the codebase? We welcome code contributions:

- **Fix bugs** - Pick an issue labeled `good first issue` or `help wanted`
- **Implement features** - Work on approved feature requests
- **Improve tests** - Add test coverage or improve existing tests
- **Enhance performance** - Optimize critical paths
- **Refactor code** - Improve code quality and maintainability

See our [Development Guide](development.md) for detailed instructions on setting up your development environment and submitting pull requests.

### Participate in Discussions

Join the conversation:

- **Answer questions** - Help others in [GitHub Discussions](https://github.com/aj-geddes/agentweave/discussions)
- **Share your projects** - Show us what you've built with AgentWeave
- **Provide feedback** - Comment on RFCs and proposals
- **Share best practices** - Teach the community what you've learned

## Getting Started as a Contributor

### 1. Read the Documentation

Familiarize yourself with AgentWeave:
- [Quickstart Guide](/agentweave/getting-started/quickstart/) - Build your first agent
- [Core Concepts](/agentweave/core-concepts/) - Understand the architecture
- [Security Model](/agentweave/security/) - Learn about security principles
- [Product Specification](../../spec.md) - Read the detailed spec

### 2. Set Up Your Development Environment

Follow our [Development Guide](development.md) to:
- Fork and clone the repository
- Install dependencies
- Run tests locally
- Configure pre-commit hooks

### 3. Pick Your First Issue

Look for issues labeled:
- **`good first issue`** - Great for newcomers
- **`help wanted`** - Community contributions welcome
- **`documentation`** - Documentation improvements
- **`bug`** - Bug fixes needed

Comment on the issue to let others know you're working on it!

### 4. Follow Our Guidelines

Please adhere to:
- **[Code of Conduct](code-of-conduct.md)** - Be respectful and inclusive
- **[Development Guide](development.md)** - Follow coding standards and practices
- **[Changelog](/agentweave/changelog/)** - See how we track changes

### 5. Submit Your Contribution

When you're ready:
1. Ensure all tests pass
2. Update documentation if needed
3. Add an entry to the changelog
4. Submit a pull request
5. Respond to review feedback

## Recognition

We value all contributions! Contributors will be:
- Listed in our [CONTRIBUTORS.md](https://github.com/aj-geddes/agentweave/blob/main/CONTRIBUTORS.md)
- Mentioned in release notes for significant contributions
- Given credit in documentation for tutorials and guides

## Questions?

Not sure where to start? Have questions?

- **Ask in Discussions** - [GitHub Discussions](https://github.com/aj-geddes/agentweave/discussions)
- **Join our chat** - [Discord/Slack link]
- **Email the maintainers** - maintainers@agentweave.io

We're here to help! Don't hesitate to reach out.

## Thank You!

Every contribution, no matter how small, helps make AgentWeave better for everyone. We appreciate you taking the time to contribute to this project.

Happy coding! 🚀

---

**Next Steps:**
- [Development Setup →](development.md)
- [Code of Conduct →](code-of-conduct.md)
- [View Changelog →](/agentweave/changelog/)
