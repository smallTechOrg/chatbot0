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
- **Gate failure: pasted phone number ID rejected.** Symptom: a correct 16-digit ID copied from
  Meta's onboarding page failed `^\d{5,20}$`. Cause: `.strip()` keeps invisible characters that web
  pages copy along (LRM marks, NBSP, zero-width). Fix: drop Unicode Zs/Cf characters and an "ID:"
  label from every pasted credential; show what was received when it still fails. Lesson: never
  validate a pasted value with only `.strip()`; test with invisible characters.

## R2 (frontend)

- **`node` not found / "No version is set".** The repo's asdf `.tool-versions` had no nodejs.
  Fix: add `nodejs 22.16.0`. Lesson: pin every runtime in `.tool-versions`.
- **BSD sed.** `sed -i 's/..' file` fails on macOS ("undefined label"). Use `sed -i ''`.
- **zsh `--include=*.py` unquoted** gives "no matches found" before grep runs. Quote globs.
- **Safety check false positive.** A long heredoc writing several .tsx files was refused as a
  "dangerous removal" although it deleted nothing. Fix: write those files with the Write tool.
- **Static export and the 404 page.** `next build` emits both `404.html` and `404/index.html`;
  `web/` must not serve the latter as a page, or `/404/` answers 200.
- **A 404 raised inside an API route** (`abort(404)`) also reaches the app's 404 handler. The
  frontend handler only answers when no route matched (`request.url_rule is None`); the rest goes
  to flask-smorest's handler so API errors stay JSON.
- **Process.** The owner merged PR #86 while R2 slice 1 was in progress; the slice was moved
  onto its own branch from `origin/main` (cherry-pick) and the rules in spec/roadmap.md updated.
- **`useSearchParams` empties the static HTML.** Symptom: pytest found no industry cards in the
  exported `/industries/` page. Cause: a client component reading the query bails out to client
  rendering, so crawlers saw an empty page. Fix: pure `IndustriesView` rendered server-side as the
  `<Suspense>` fallback, and a small client wrapper that adds the highlight. Lesson: assert on the
  exported HTML, not just on components.
- **React inserts `<!-- -->` between adjacent text nodes**, so `$4<span>` is `$<!-- -->4<span>` in the
  export. Export tests strip the separators before matching.
- **Canonical URLs get a trailing slash** from Next metadata when `trailingSlash: true`. The
  canonical, og:url and sitemap now all end in `/` (both forms serve 200, no redirect).
- **Slices that change what customers copy must ship together.** The sign-up snippet cannot point at
  chatbot0's `/embed.js` before slice 4 serves it, so slice 3 keeps the zer0 host until then.
- **PRs run no CI.** deploy.yml triggers on push to main/staging only, so a PR shows "no checks".
  A slice is gated by pushing the branch merge to `staging` first.
