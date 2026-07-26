# Agent Instructions

All coding agents working in this repository must follow these rules.

## Required Reading

Before changing code, read:

- README.md
- docs/PROJECT_CHARTER.md

## Working Rules

- Work one phase at a time.
- Never expose or request secrets.
- Never hardcode credentials.
- Never include credentials, tokens, connection strings, account IDs, private keys, certificates, or other sensitive values in code or documentation.
- Never add automatic destructive AWS actions.
- Require human approval for remediation decisions.
- Use synthetic data by default.
- Keep documentation truthful about implemented versus planned features.
- Do not claim that planned features are implemented until they exist and have been verified.
- Run tests and security checks before suggesting a commit.
- Do not commit or push unless the user explicitly asks.

## Cloud Safety

Cloud Nexus OrphanProof must remain read-only by default. Any remediation workflow must present evidence, recommended action, and risk context for human approval before action is taken.
