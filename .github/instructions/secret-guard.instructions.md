---
applyTo: '**'
description: 'Prevent secrets (API keys, tokens, passwords, private keys) from leaking into context, tool output, or spawned processes.'
---

## Secret Handling (Always On)

These rules protect secrets at all times. They are subordinate only to an explicit, direct user command.

-   **Never Read Secret Files**: Do not open or print the contents of files that commonly hold credentials. This includes `.env`, `.env.*`, `.netrc`, `.npmrc`, `.pypirc`; any `.pem`, `.key`, `.p12`, `.pfx`, `.crt`, `.cer`; and any filename containing `password`, `secret`, `credential`, or `private_key`/`private-key`. If asked to inspect such a file, decline and explain it may contain secrets.
-   **Redact Secret Values**: Before surfacing any file content, command result, or tool output, replace secret values with `[REDACTED]`. This includes `NAME=value` lines where `NAME` ends in `KEY`, `TOKEN`, `SECRET`, `PASSWORD`, `CREDENTIAL`, `API_KEY`, or `AUTH` (e.g. `CLOUD_API_KEY=sk-abc123` → `CLOUD_API_KEY=[REDACTED]`).
-   **Hide Secret Files in Listings**: When listing a directory, omit secret-bearing files (e.g. `.env*`, `.netrc`, `.npmrc`, `.pypirc`) rather than revealing their existence.
-   **Sanitize Subprocess Environments**: Do not expose secret environment variables to spawned commands. Strip variables whose names end in `KEY`, `TOKEN`, `SECRET`, `PASSWORD`, `CREDENTIAL`, `AUTH`, or `PASS` so processes cannot read them via `$VAR` or `printenv`.
-   **Never Commit Secrets**: Do not write credentials, tokens, or keys into source code, configuration, or commit messages.
-   **Authenticate by Reference, Never by Value**: When a task needs an API token, MCP token, password, or key, do not read, request, or handle the value. Pass a credential *reference* (a name) and let a trusted broker resolve it from the OS keyring and inject it into the request. If no keyring entry exists, ask the user to store it themselves (e.g. `keyring set agent-secrets <name>`) — never accept a pasted secret into the conversation.

For the full procedure and a keyring broker implementation, use the `secret-guard` skill.
