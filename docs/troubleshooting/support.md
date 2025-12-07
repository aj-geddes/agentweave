---
layout: page
title: Getting Help
description: How to get support for AgentWeave
nav_order: 4
parent: Troubleshooting
---

# Getting Help

This guide explains how to get help with AgentWeave, whether you have questions, found a bug, or want to contribute.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Before Asking for Help

Before reaching out, try these steps:

### 1. Search Existing Resources

- **[Documentation](../index.md)** - Comprehensive guides and references
- **[FAQ](faq.md)** - Frequently asked questions
- **[Common Issues](common-issues.md)** - Quick solutions to known problems
- **[GitHub Issues](https://github.com/aj-geddes/agentweave/issues)** - Known bugs and feature requests
- **[GitHub Discussions](https://github.com/aj-geddes/agentweave/discussions)** - Community Q&A

### 2. Enable Debug Logging

Get more information about the problem:

```yaml
# config.yaml
observability:
  logging:
    level: "DEBUG"
    format: "json"
```

### 3. Validate Your Configuration

Ensure your configuration is correct:

```bash
agentweave validate config.yaml --strict
```

### 4. Check Infrastructure

Verify SPIRE and OPA are running:

```bash
# SPIRE health
docker exec spire-server spire-server healthcheck
docker exec spire-agent spire-agent healthcheck

# OPA health
curl http://localhost:8181/health

# Agent health
agentweave health --verbose
```

---

## Community Support

### GitHub Discussions

**Best for:** Questions, ideas, and general discussion

**URL:** [github.com/aj-geddes/agentweave/discussions](https://github.com/aj-geddes/agentweave/discussions)

**Categories:**
- **Q&A** - Ask questions, get answers
- **Show and Tell** - Share what you've built
- **Ideas** - Propose new features
- **General** - Everything else

**How to ask a good question:**

1. **Search first** - Your question may already be answered
2. **Clear title** - Describe the problem in the title
3. **Provide context** - What are you trying to do?
4. **Include details** - Version, environment, configuration
5. **Show what you tried** - What have you attempted?

**Example:**
```markdown
# Cannot connect to SPIRE agent in Kubernetes

## Environment
- AgentWeave version: 0.3.0
- Kubernetes: 1.28
- SPIRE version: 1.8.0

## What I'm trying to do
Deploy an agent to Kubernetes that connects to SPIRE agent via hostPath volume.

## What I've tried
1. Mounted `/run/spire/sockets` as hostPath volume
2. Set SPIFFE_ENDPOINT_SOCKET env var
3. Verified socket exists in pod: `ls -l /run/spire/sockets/agent.sock`

## Error
```
ERROR: Failed to connect to SPIRE agent
ConnectionRefusedError: [Errno 111] Connection refused
```

## Configuration
```yaml
# (sanitized config)
```

## Question
Is there a permission issue with the hostPath mount?
```

### Discord Community

**Best for:** Real-time chat, quick questions

**URL:** [discord.gg/agentweave](https://discord.gg/agentweave)

**Channels:**
- **#general** - General discussion
- **#help** - Get help with issues
- **#show-off** - Show what you've built
- **#security** - Security-related questions
- **#development** - Development and contributing

**Guidelines:**
- Be respectful and patient
- Don't post the same question in multiple channels
- Use threads for longer discussions
- Share solutions when you find them

### Stack Overflow

**Best for:** Detailed technical questions

**URL:** [stackoverflow.com/questions/tagged/agentweave](https://stackoverflow.com/questions/tagged/agentweave)

**Tag:** `agentweave`

**How to ask:**
1. Use the `agentweave` tag
2. Follow Stack Overflow's [question guidelines](https://stackoverflow.com/help/how-to-ask)
3. Include minimal reproducible example
4. Show what you've tried

---

## Bug Reports

### GitHub Issues

**Best for:** Bugs, regressions, unexpected behavior

**URL:** [github.com/agentweave/agentweave/issues/new](https://github.com/agentweave/agentweave/issues/new)

### How to Write a Good Bug Report

A good bug report helps us fix issues quickly.

**Required information:**
1. AgentWeave version
2. Python version
3. Operating system
4. Steps to reproduce
5. Expected behavior
6. Actual behavior
7. Error messages and stack traces

**Use this template:**

```markdown
## Bug Description
Clear, concise description of the bug.

## Environment
- **AgentWeave version:** (run `agentweave --version`)
- **Python version:** (run `python --version`)
- **OS:** (e.g., Ubuntu 22.04, macOS 13.0, Windows 11)
- **Installation method:** (pip, source, Docker)

## Steps to Reproduce
1. Create config.yaml with...
2. Run `agentweave serve config.yaml`
3. Call agent with...
4. See error

## Expected Behavior
What you expected to happen.

## Actual Behavior
What actually happened.

## Error Messages
```
Full error message and stack trace
```

## Configuration
```yaml
# config.yaml (sanitized - remove secrets)
agent:
  name: "test-agent"
  # ...
```

## Code Sample
```python
# Minimal code to reproduce the issue
from agentweave import SecureAgent

# ...
```

## Logs
```
Full debug logs if available
```

## Additional Context
Any other relevant information:
- Does it happen consistently or intermittently?
- Did this work in a previous version?
- Any workarounds you've found?
```

### Example Bug Report

```markdown
## Bug Description
Agent crashes when SVID rotation occurs during active request

## Environment
- **AgentWeave version:** 0.3.0
- **Python version:** 3.11.5
- **OS:** Ubuntu 22.04
- **Installation method:** pip

## Steps to Reproduce
1. Configure agent with 1-minute SVID TTL
2. Start agent: `agentweave serve config.yaml`
3. Make long-running request (>30s)
4. SVID rotation occurs during request
5. Agent crashes with error

## Expected Behavior
Request should complete successfully. New SVID should be used for subsequent requests.

## Actual Behavior
Agent crashes with SSLError during SVID rotation.

## Error Messages
```
ERROR: SSL error during request
Traceback (most recent call last):
  File "agentweave/transport/mtls.py", line 45, in handle_request
    response = await handler(request)
  ...
ssl.SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed
```

## Configuration
```yaml
agent:
  name: "test-agent"
  trust_domain: "example.com"

identity:
  provider: "spiffe"

server:
  port: 8443
```

## Additional Context
- Happens consistently when rotation occurs during request
- Workaround: Set longer SVID TTL (1 hour works)
- Started happening after upgrading from 0.2.5 to 0.3.0
```

### What Happens Next

After submitting a bug:

1. **Triage** - Maintainers review within 48 hours
2. **Label** - Issue tagged with priority and category
3. **Investigation** - Maintainers or community investigate
4. **Fix** - Pull request created to fix
5. **Release** - Fix included in next release
6. **Close** - Issue closed with reference to fix

**Track your issue:**
- Watch the issue for updates
- Respond to questions from maintainers
- Test fixes when available

---

## Feature Requests

### GitHub Discussions

**Best for:** Feature ideas and proposals

**URL:** [github.com/agentweave/agentweave/discussions/categories/ideas](https://github.com/agentweave/agentweave/discussions/categories/ideas)

### How to Propose a Feature

**Use this template:**

```markdown
## Problem Statement
What problem does this solve? Why is it needed?

## Proposed Solution
How would this feature work?

## Alternatives Considered
What other approaches did you consider?

## Use Cases
Real-world examples of how this would be used.

## Implementation Ideas
Any thoughts on how to implement this?

## Breaking Changes
Would this break existing code?
```

### Example Feature Request

```markdown
## Problem Statement
Currently, agents must explicitly specify target SPIFFE IDs when calling other agents. In dynamic environments, it would be useful to discover agents by capability rather than by ID.

## Proposed Solution
Add capability-based discovery:

```python
# Instead of:
await agent.call_agent(
    target="spiffe://example.com/agent/specific-agent",
    task_type="process"
)

# Allow:
await agent.discover_and_call(
    capability="process_data",
    payload={"data": "..."}
)
```

## Alternatives Considered
1. Service registry (more complex, requires new infrastructure)
2. DNS-based discovery (less flexible)
3. Static configuration (not dynamic)

## Use Cases
1. **Auto-scaling**: New agent instances automatically discovered
2. **Blue/Green**: Route to different versions by capability tags
3. **Multi-region**: Discover nearest agent with capability

## Implementation Ideas
- Extend Agent Card with capability tags
- Add discovery service or use existing registry
- Cache discovered agents with TTL

## Breaking Changes
No breaking changes - this would be additive.
```

---

## Security Issues

**DO NOT** report security vulnerabilities in public issues.

### Private Disclosure

**Email:** security@agentweave.io

**Include:**
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

**PGP Key:** Available at [agentweave.io/security.txt](https://agentweave.io/security.txt)

### What to Expect

1. **Acknowledgment** - Within 48 hours
2. **Investigation** - 1-2 weeks
3. **Fix** - Coordinated disclosure
4. **Credit** - Recognition in release notes (if desired)

### Responsible Disclosure

We follow a 90-day disclosure timeline:

1. **Day 0**: Report received
2. **Day 7**: Fix developed and tested
3. **Day 14**: Fix released
4. **Day 21**: Public disclosure (or 90 days, whichever is sooner)

---

## Contributing

### Ways to Contribute

**Code:**
- Fix bugs
- Implement features
- Improve performance
- Add tests

**Documentation:**
- Fix typos and errors
- Add examples
- Improve clarity
- Translate to other languages

**Community:**
- Answer questions
- Help with triage
- Review pull requests
- Share knowledge

### Getting Started

1. **Read the Contributing Guide**: [CONTRIBUTING.md](https://github.com/agentweave/agentweave/blob/main/CONTRIBUTING.md)
2. **Set up development environment**: [Development Guide](https://github.com/agentweave/agentweave/blob/main/docs/development.md)
3. **Find an issue**: Look for `good first issue` label
4. **Ask questions**: Comment on the issue before starting

### Pull Request Process

1. **Fork** the repository
2. **Create branch**: `git checkout -b fix/your-fix`
3. **Make changes**: Write code, add tests
4. **Test**: Run `pytest` and ensure all pass
5. **Commit**: Use clear commit messages
6. **Push**: `git push origin fix/your-fix`
7. **Create PR**: Open pull request with description

**PR checklist:**
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] All tests pass
- [ ] Code follows style guide
- [ ] Commits are clean and descriptive

### Code Review

PRs are reviewed by maintainers:
- Expect feedback within 3-5 days
- Address review comments
- Be patient and respectful
- Learn from the process

---

## Professional Support

### Enterprise Support

For organizations requiring:
- SLA-backed support
- Custom development
- Training and consulting
- Security audits
- Priority bug fixes

**Contact:** enterprise@agentweave.io

### Services Offered

**Support Tiers:**
- **Bronze**: Email support, 48-hour response
- **Silver**: Email + Slack, 24-hour response, quarterly reviews
- **Gold**: 24/7 support, 4-hour response, dedicated engineer

**Professional Services:**
- Architecture review
- Custom integrations
- Security hardening
- Performance optimization
- Training workshops

**Training:**
- AgentWeave fundamentals (1 day)
- Security deep-dive (2 days)
- Custom workshops (tailored)

---

## Resources

### Official Resources

- **Website**: [agentweave.io](https://agentweave.io)
- **Documentation**: [docs.agentweave.io](https://docs.agentweave.io)
- **GitHub**: [github.com/agentweave/agentweave](https://github.com/agentweave/agentweave)
- **Blog**: [blog.agentweave.io](https://blog.agentweave.io)

### Community Resources

- **Discord**: [discord.gg/agentweave](https://discord.gg/agentweave)
- **Twitter**: [@agentweave](https://twitter.com/agentweave)
- **YouTube**: [youtube.com/@agentweave](https://youtube.com/@agentweave)
- **Stack Overflow**: [stackoverflow.com/questions/tagged/agentweave](https://stackoverflow.com/questions/tagged/agentweave)

### Related Projects

- **SPIFFE**: [spiffe.io](https://spiffe.io)
- **SPIRE**: [spiffe.io/docs/latest/spire/](https://spiffe.io/docs/latest/spire/)
- **OPA**: [openpolicyagent.org](https://openpolicyagent.org)
- **A2A Protocol**: [a2a-protocol.org](https://a2a-protocol.org)

---

## Communication Guidelines

### Be Respectful

- Treat everyone with respect
- Assume good intentions
- Be patient with newcomers
- Celebrate contributions

### Be Clear

- Use clear, concise language
- Provide context and details
- Include examples when possible
- Format code and logs properly

### Be Helpful

- Share knowledge generously
- Help others when you can
- Document solutions you find
- Contribute back when possible

### Be Patient

- Maintainers are volunteers (mostly)
- Reviews take time
- Complex issues take longer
- Not all requests can be accommodated

---

## Next Steps

**Found a bug?** [Report it on GitHub →](https://github.com/agentweave/agentweave/issues/new)

**Have a question?** [Ask in Discussions →](https://github.com/agentweave/agentweave/discussions)

**Want to contribute?** [Read Contributing Guide →](https://github.com/agentweave/agentweave/blob/main/CONTRIBUTING.md)

**Need help now?** [Join Discord →](https://discord.gg/agentweave)

---

**Back to:** [Troubleshooting Overview](index.md)
