# Build journal: chatbot0 WhatsApp (zero-shot-build)

Run started 2026-11-23 22:22 IST. Harness-improvement log, not an app changelog.

- **Intake skipped too early.** Symptom: started coding after one question round because the
  skill allows skipping scope intake for an existing project. The user stopped it ("we need to do
  proper intake"). Later rounds changed the design: multi-tenant connections, encrypted
  per-tenant credentials, an admin page. Lesson: for "add a capability", still run the full
  product rounds when the capability opens new product surface (a new channel, tenants).
- **User mistook the access token for the app secret.** The pasted Graph API curl carried only
  the access token. Intake should ask for each Meta credential by its dashboard location.
- **`claude` CLI not on the tool shell's PATH.** `claude mcp add ...` from a user message failed
  with "command not found"; the user has to run it in their own terminal.
- **Stale venv shebangs.** The repo was renamed, so `venv/bin/pip` and `venv/bin/gunicorn` point
  at a missing interpreter. Use `venv/bin/python -m <tool>`.
- **Env prefix with `||`.** `A=1 cmd1 || cmd2` does not pass A to cmd2: the first boot gate
  failed with "APP_ENV is not set". Use `env A=1 cmd`.
