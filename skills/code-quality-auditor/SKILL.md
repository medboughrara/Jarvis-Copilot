---
name: code-quality-auditor
description: "Automated linting, static code analysis, security auditing, and refactoring guidelines."
---

# Code Quality & Security Auditor Playbook

When reviewing or refactoring codebase source files:

1. **Security & Input Sanitization**:
   - Verify path arguments use `AgentShieldGuard` path bounds validation (`agent/security.py`).
   - Ensure user input strings are sanitized before passing to process execution commands.

2. **Code Cleanliness & Type Safety**:
   - Enforce Python 3.12 type annotations (`Dict[str, Any]`, `List[str]`, `Optional[str]`).
   - Remove unused variable declarations and dead imports.
