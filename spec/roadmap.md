# chatbot0 roadmap (planned 2026-11-24)

Executable plan for the phases after WhatsApp phase 1. Written so a fresh session
(or another model) can implement it without re-deciding anything. Decisions below
were made by the product owner during intake; do not re-litigate them. Where this
plan says **Assumed**, it is a planner default the owner has not confirmed: build it,
and list it in the PR body under "Assumptions".

Done so far (branch `feature/whatsapp-bot-20261123-2222-v0.1`, PR #86 → `main`):
- Phase 1: the WhatsApp channel (per-connection webhooks, encrypted credentials, Jinja admin page).
- R1: `code/` moved to the repo root.

Order of the remaining work: **Q (quality) → R2 (frontend) → Phase 3 (multi-tenant)**.

## Ground rules for autonomous work

- **Branch:** keep working on `feature/whatsapp-bot-20261123-2222-v0.1` (PR #86 → `main`).
  The owner chose to fold the restructure into this PR. Commit per slice, push after
  every green gate, and keep the PR body current (what's done, how to test, deferred).
- **Never** merge to `main`, deploy production, edit production GitHub variables or secrets,
  rotate `CHATBOT0_SECRET_KEY`, or delete data.
- **Staging is fine.** Merge the feature branch into `staging` and push it (that
  auto-deploys `zero-sales-agent-staging`) after each phase passes locally, then smoke-test
  the staging URL with curl. Staging shares the production Cloud SQL instance but uses
  its own database (`staging_chat_db`), so schema changes there are expected.
- **zer0-frontend-web:** make the changes on a branch and open a PR. **Do not merge it.**
  That repo deploys zer0.smalltech.in from `main`, and live customer widgets load from it.
- **Gates:** run `venv/bin/python -m pytest -q test` (local Postgres:
  `DATABASE_URL=postgresql://$(whoami)@localhost:5432/ GROQ_API_KEY=dummy`). Run `ruff`
  on changed Python files. Run `npm run build` in `frontend/`. Do a local gunicorn boot
  (`env APP_ENV=local DB_NAME=chatdb DASHBOARD_URL=... CHATBOT0_SECRET_KEY=x
  CHATBOT0_ADMIN_PASSWORD=y venv/bin/python -m gunicorn --bind :5099 app:app`) plus a
  curl smoke test. Never claim a gate passed without reading its output.
- **Journal:** add every friction point to `NOTES.md` (symptom → fix → lesson).
- **Secrets:** never read `.env`, never print secrets, never commit them.
- **Stuck** (a test you can't get green after 3 honest attempts, or a decision this plan
  doesn't cover): stop, write the question at the top of the PR body under "Waiting on
  owner", and move on to the next independent slice.

---

## Q — Code structure and quality (do this **before** R2)

**Goal:** a codebase the new work can follow. **No behaviour change**: the existing test
suite is the safety net. Run it after every step, and fix forward.

1. **Tooling first.**
   - Add `pyproject.toml` with ruff config: `line-length = 120`,
     `target-version = "py312"`, lint `select = ["E","F","I","B","UP","SIM","RUF"]`
     (ignore only what is justified in a comment).
   - Run `ruff check --fix` and `ruff format`, then fix the remaining errors by hand.
     Today there are 27 (E701, F401, F811, F841).
   - CI test job: add `ruff check .` and `ruff format --check .` before pytest.
   - Commit the formatting on its own ("ruff format, no code change"), so review diffs stay
     readable.
2. **Package layout.** Move the flat root modules into packages. Fix the imports and the
   tests' monkeypatch targets.
   ```
   app.py                 create_app() only; no route definitions (move /chat-ui into api/)
   core/                  config.py, db_pool.py, schema.py (was db.py), crypto.py, llm.py, logging.py
   chat/                  engine.py (llm_api), history.py, prompts.py (system_prompt + prompts_table),
                          lead_capture.py (conversation_processor), contact_validation.py
   leads/                 repository.py (leads.py + leads_update.py)
   summary/               periodic.py (periodic_summary), slack.py (slack_notify), scheduler.py
   domains/  whatsapp/    already packages; keep the layering
   api/                   HTTP only: parse, call a service, shape the response. No SQL in api/.
   ```
   Later phases add `auth/`, `tenancy/` and `web/` in the same style. Layering rule:
   `api → service → repository`. SQL lives only in repository modules (or `core/schema.py`).
3. **One LLM factory.** `core/llm.py: get_chat_model()` replaces the three `ChatGroq(...)`
   constructions (llm_api, conversation_processor, periodic_summary). The backup model
   (`GROQ_BACKUP_MODEL_NAME`) is wired there via LangChain `.with_fallbacks()` when set.
4. **Fix the fake-async lead capture.** `_process_conversation_async` blocks the reply,
   because `with ThreadPoolExecutor(...)` waits on exit.
   - Run contact detection **concurrently with** the reply LLM call, by submitting it
     first and collecting it after. That keeps everything inside the request, which
     Cloud Run needs because it throttles CPU after the response, while cutting reply
     latency.
   - Add a test that the reply doesn't wait for detection beyond the reply's own duration
     (stub both LLM calls with sleeps).
5. **Logging, not print.**
   - `core/logging.py` configures `logging` once in `create_app`: one line per record,
     level from `LOG_LEVEL` (default INFO), output to stdout for Cloud Logging.
   - Replace all ~122 `print(` calls with `logger = logging.getLogger(__name__)`, at the
     right level (`exception()` instead of `print(traceback.format_exc())`).
   - Keep the existing `[TAG]` message prefixes so log searches still work.
   - Never log secrets. Contact details (emails, phones) get logged at DEBUG only.
6. **Dead code and hygiene.** Remove commented-out code (e.g. in `system_prompt.py`) and
   unused functions. Fix the misleading comments. Add type hints on every public
   function you touch. Remove the stale `deploy.md` if `DEPLOYMENT.md` covers it (check
   first).
7. **Tests.**
   - Mirror the package layout under `test/`, and move shared fixtures (DB cleanup, LLM
     stubs, signed WhatsApp payloads) into `test/conftest.py`.
   - Keep every existing assertion. Count the tests before and after: the number must
     not drop.

**Standards for everything written in R2 and Phase 3 (reviewers will check):**
- Python:
  - type hints on public functions;
  - no SQL outside repositories;
  - no `print`;
  - exceptions are caught at the API boundary only;
  - a docstring on every module saying what it owns;
  - functions under about 50 lines;
  - each new behaviour gets a test in the same commit.
- Frontend:
  - TypeScript `strict`, with `tsc --noEmit` and `next lint` in CI;
  - no `any`;
  - data fetching only through `src/lib/api.ts`;
  - components in `src/components/`, with page files kept thin;
  - Vitest for `lib/` and non-trivial hooks (CI runs `npm test`);
  - accessible markup (labels, focus states, keyboard use);
  - no inline styles except dynamic colours.
- Before each phase hand-off, run a review pass: re-read the diff of the whole phase as a
  reviewer, using the `/code-review` skill if available, otherwise by hand. Fix what it
  finds, and note anything deferred in the PR body.

**Q gate:**
- `ruff check` and `ruff format --check` clean; pytest green with the same or a higher
  test count.
- Local gunicorn boot + curl smoke test: `/health`, `/chat` with the stubbed key returns
  a JSON error and not a crash, and the WhatsApp webhook handshake.
- CI green on staging, and the staging smoke test passes.

---

## R2 — Frontend in Next.js (`frontend/`), served by Flask

**Goal:** everything a person sees on chatbot0 is a React/Next.js app in `frontend/`.
Flask serves only its static export and JSON APIs. Every chatbot0 page leaves
zer0-frontend-web.

### Architecture
- `frontend/`: Next.js (App Router, TypeScript, Tailwind 4) with `output: "export"`,
  `trailingSlash: true` and `images.unoptimized: true`. The pinned versions match
  zer0-frontend-web (`next ^15.3`, `react ^19.2`).
- **Build:** the Dockerfile gets a first stage, `FROM node:22-slim AS web`, that runs
  `npm ci && npm run build` in `frontend/` and produces `frontend/out`. The Python stage
  then does `COPY --from=web /web/out /app/frontend_out`. `.dockerignore` excludes
  `frontend/node_modules`, `frontend/.next` and `frontend/out`.
- **CI** (`deploy.yml`, test job): add a step that sets up Node 22 and runs
  `npm ci && npm run build` in `frontend/`, so a broken frontend fails before deploy.
- **Serving:** a new blueprint, `web/__init__.py` (Python package name `web`; do not
  collide with `frontend/`), registered last. For GET/HEAD requests that no API route
  matched, it serves files from `FRONTEND_DIR` (config, default `frontend_out`).
  Lookup order: `<path>`, then `<path>/index.html`, then `<path>.html`. If none exists,
  it serves `404.html` with status 404.
  - Implement it as `app.errorhandler(404)`, plus an explicit route for `/` on the
    chatbot0 host. That way API routes always win, and unknown API paths under `/api/`
    still get JSON 404s.
  - Cache headers: `/_next/static/*` gets `Cache-Control: public, max-age=31536000,
    immutable`; HTML gets `no-cache`.
- **Hosts.** Today `register_host_routing` maps the root of `chatbot0.smalltech.in` to
  the Jinja pages, and `/` on the run.app URL is the legacy Swagger UI. New rule:
  - On chatbot0 hosts, the Next app is served at `/`.
  - On other hosts (run.app), the Next app is served under `/chatbot0/` via Next
    `basePath`? **No.** One export cannot serve two base paths.
  - Instead, serve the export at the root on **all** hosts and move the legacy Swagger UI
    to `/api/legacy-docs`. Keep `/api/docs` (smorest) as it is.
  - Old `/chatbot0/<page>` URLs get a 301 to `/<page>`.
  - Update `api/swagger.py` and every test that asserts `/` is Swagger.
- **API base:** the frontend calls same-origin, root-absolute paths (`/chat`, `/history`,
  …). There's no `NEXT_PUBLIC_API_URL`, except `frontend/.env.development` for
  `next dev`, pointing at `http://localhost:5001`. For local dev, add `rewrites` in
  `next.config.ts` that apply only in development.

### Slices (each slice = its pages + tests; commit each)
1. **Skeleton + serving:** the Next app with a layout, global CSS (port the tokens from
   `static/chatbot0/css/chatbot0.css`), and the `web` blueprint. Also the Dockerfile
   stage, the CI build step, and pytest tests for the serving blueprint using a fixture
   `frontend_out` directory: file found, index.html fallback, 404 page, API still wins,
   cache headers.
2. **Marketing pages:** landing, pricing, sales, support, industries (`?industry=`
   highlight, now client-side), about, robots.txt, sitemap.xml, and the Open Graph and
   canonical tags.
   - Port them one-to-one from `templates/chatbot0/*.html` and `chatbot0/content.py`.
     Keep the copy identical; plans move to `frontend/src/content/`.
   - Use the Next metadata API per page. Keep Google Analytics as it is
     (`st-analytics.js`).
   - Delete the Jinja pages and `chatbot0/` once the ports serve. Update
     `test/test_chatbot0_pages.py` to assert the exported HTML (built in CI) or, more
     simply, to test the blueprint against fixture files. The real check is a curl smoke
     test of the built app.
3. **Sign-up page:** port `static/chatbot0/js/signup.js` and `signup.html` to React,
   keeping the same behaviour for now. Phase 3 changes it into account creation.
4. **Chat widget:**
   - Port `zer0-frontend-web/code/src/app/embed/*` (widget.tsx, colorTheme.ts,
     widget.module.css), `chat/`, the `hooks/` the widget uses, and
     `public/embed.js` → `frontend/public/embed.js`.
   - `embed.js` default `data-chat-url` becomes `https://chatbot0.smalltech.in/embed/`,
     and the sign-up page's snippet uses `https://chatbot0.smalltech.in/embed.js`.
   - The widget calls `/chat` and `/history` with the host site's origin exactly as
     today. Read `embed/widget.tsx` and `hooks/useChat.ts` for how it passes `origin`,
     and keep that contract.
5. **zer0-frontend-web PR (do not merge):**
   - Remove `embed/`, `chat/`, `dashboard/`, `signup/` and the other chatbot0 pages.
   - Replace `public/embed.js` with a **stub loader**. It finds its own `<script>` tag,
     copies every `data-*` attribute, rewrites `data-chat-url` if it points at
     `zer0.smalltech.in/embed`, and injects
     `<script src="https://chatbot0.smalltech.in/embed.js">` with those attributes.
     Every installed widget keeps working with no change on customer sites.
   - Turn `/embed` into a page that redirects to `https://chatbot0.smalltech.in/embed/`
     with the same query string (MovedTo-style, as already used there).
   - `/dashboard` → MovedTo `https://chatbot0.smalltech.in/dashboard/`.
   - In the PR body, state that it must merge **only after** the chatbot0 production
     deploy serves `/embed.js` and `/embed/`.

**R2 gate:**
- pytest green, the frontend build green, and a local boot where curl returns 200 with
  the right `<title>` for `/`, `/pricing/`, `/signup/`, `/embed/` and `/embed.js`.
- `/health` and `/chat` behave as before.
- Staging deploy is green, and the same curls pass on the staging URL.
- Test the widget end to end on staging: load `/embed/?...` with a known origin parameter
  and POST `/chat` for the `example.com` / `COMMON` domain. The real LLM is available on
  staging.

### R2 risks
- Tests that assert `/` is Swagger, or that the Jinja pages exist, must be updated.
  Don't delete tests silently: move each assertion to the new location.
- `register_host_routing`, `PAGE_PATHS` and the sitemap logic move into the frontend.
  Remove the Python versions once nothing uses them.

---

## Phase 3 — Multi-tenant chatbot0

**Owner decisions (binding):**
- Tenants have accounts with an **email + password** login. One tenant can own **many
  domains**, and sub-domains inherit prompts through `domains.parent` as today.
- Self sign-up still works, but a new tenant is **not enabled**. Until a chatbot0 admin
  enables it, the tenant can:
  - **log in and see its own dashboard and leads** (read-only on prompts and WhatsApp);
  - get widget answers up to a **trial cap** (Assumed: 20 conversations, a per-tenant
    column). After the cap, `/chat` replies with a fixed message ("This assistant isn't
    active yet.") and makes no LLM call.
- An enabled tenant can also edit its prompts and company info, and connect WhatsApp
  (self-serve, the same flow as the admin page, scoped to its own domains).
- **Cutover in one release:** the new dashboard ships in the same deploy that locks every
  data API behind login. The zer0-frontend-web dashboard dies (its PR from R2 redirects).
- **All existing domains** (COMMON, DEXTER, SMALLTECH, ZERO and every earlier sign-up)
  belong to **one smallTech tenant**, which is enabled.
- **No email service yet.** The admin generates invite and reset links in the admin UI
  and sends them by hand.
- **Admins** are user accounts with `is_admin`. Admins see and manage all tenants.

### Data model (add to `db.py` bootstrap, idempotent)
```sql
CREATE TABLE IF NOT EXISTS tenants (
  id SERIAL PRIMARY KEY, name TEXT NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT FALSE, enabled_at TIMESTAMPTZ,
  trial_conversation_limit INT NOT NULL DEFAULT 20,
  created_at TIMESTAMPTZ DEFAULT NOW());
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY, tenant_id INT NOT NULL REFERENCES tenants(id),
  email TEXT NOT NULL, password_hash TEXT,            -- NULL until the invite is accepted
  is_admin BOOLEAN NOT NULL DEFAULT FALSE,
  session_version INT NOT NULL DEFAULT 1,             -- bump to sign out everywhere
  created_at TIMESTAMPTZ DEFAULT NOW(), last_login_at TIMESTAMPTZ);
CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower ON users (lower(email));
CREATE TABLE IF NOT EXISTS user_tokens (               -- invite / reset links
  token_hash TEXT PRIMARY KEY, user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  purpose TEXT NOT NULL CHECK (purpose IN ('invite','reset')),
  expires_at TIMESTAMPTZ NOT NULL, used_at TIMESTAMPTZ);
ALTER TABLE domains ADD COLUMN IF NOT EXISTS tenant_id INT REFERENCES tenants(id);
```
**Migration** (same bootstrap, idempotent):
- If no tenant named `smallTech` exists, create it with `enabled = true`.
- `UPDATE domains SET tenant_id = <smallTech> WHERE tenant_id IS NULL`.
- A domain's tenant is `domains.tenant_id`; leads are scoped through
  `chat_info.domain = domains.key`. Note that `key` isn't unique: the www row shares it.
  Scope with `domain IN (SELECT key FROM domains WHERE tenant_id = %s)`.

### Auth (`auth/` package)
- Passwords: `werkzeug.security.generate_password_hash` (scrypt) and
  `check_password_hash`. Require at least 10 characters.
- Session: the Flask signed cookie, already configured in `app.py`, holding `uid`, `sv`
  (session_version) and `csrf`. `current_user()` loads the user and checks
  `session_version`. The cookie stays HttpOnly, SameSite=Lax, and Secure outside local.
- CSRF:
  - Every state-changing JSON API under session auth requires the `X-CSRF-Token` header
    to equal `session["csrf"]`. `GET /api/auth/me` returns the token.
  - CORS is `CORS(app)` (no credentials), so cross-site requests can't read the
    responses, and SameSite=Lax blocks cross-site cookie POSTs. Keep both.
- Login rate limit: Assumed 10 failed attempts per email per 15 minutes, counted in a
  small `login_attempts` table. Answer with a generic "wrong email or password".
- Tokens: `secrets.token_urlsafe(32)`, stored as a sha256 hash. Invites expire in 7
  days, resets in 24 hours, and each is single-use.
- **Bootstrap admin:** `POST /api/auth/bootstrap` with
  `{password: CHATBOT0_ADMIN_PASSWORD, email, new_password}` works **only while no admin
  user exists**. It creates an admin user in the smallTech tenant. The frontend
  `/login/` page shows a "first-time setup" link when `GET /api/auth/status` reports
  `{needs_bootstrap: true}`. After bootstrap, the shared password no longer logs anyone
  in, and the old Jinja `/chatbot0/admin/*` pages are deleted.

### APIs (JSON, all under session auth unless marked public)
| Method | Path | Who | Notes |
|---|---|---|---|
| GET | /api/auth/status | public | `{needs_bootstrap}` |
| POST | /api/auth/bootstrap | public, one-time | see above |
| POST | /api/auth/login, /api/auth/logout | public / user | |
| GET | /api/auth/me | user | user, tenant (enabled, trial usage), domains, csrf |
| POST | /api/auth/accept | public (token) | set password from an invite or reset token |
| POST | /api/signup | public | creates tenant (disabled) + user + domain + company prompt; logs in; Slack `notify_signup`; 409 if the email or website exists |
| GET | /api/leads | user | the tenant's leads (admin: all, `?tenant_id=`). Same fields as `leads.py` + channel + tenant |
| PATCH | /api/leads/<session_id> | user | status / remarks / is_active; tenant must own the lead |
| GET | /api/leads/<session_id>/history | user | read-only (never inserts the intro the way `/history` does) |
| GET/POST | /api/domains | user | list own / add a website (enabled tenants; Assumed: max 10) |
| GET/PUT | /api/domains/<key>/prompts | user (enabled) | `company`, `base-prompt`, `intro-message` for `sales` |
| GET/POST/PATCH | /api/whatsapp/connections[...] | user (enabled, own domains) / admin | port `admin/__init__.py` logic to JSON |
| GET | /api/admin/tenants | admin | with usage (conversation count), enabled, users |
| PATCH | /api/admin/tenants/<id> | admin | enabled, trial_conversation_limit, name |
| POST | /api/admin/tenants/<id>/users | admin | add a user → returns an invite link |
| POST | /api/admin/users/<id>/reset-link | admin | returns a reset link |
| PATCH | /api/admin/domains/<key> | admin | move a domain to another tenant |

**Lock or remove these legacy public endpoints:**
- `GET /chat-info`, `PATCH /chat-info`, `PATCH /chat-info/contact`, `GET /prompts`,
  `POST /prompt`, `GET /domains/`, `GET /domains/<id>` and `POST /domains/` become
  **admin-only**.
  - Keep the routes so old tools get a clear 401 or 403, not a 404.
  - The sign-up page switches to `POST /api/signup`.
  - Update `static/swagger.yaml` and the smorest docs.
- `/chat` and `/history` stay public: the widget needs them, and the session UUID is the
  capability.
- `/whatsapp/webhook/*` stays public and signature-checked.
- `/jobs/*` keeps OIDC.

**Trial cap:** `tenancy.conversation_allowed(domain_key, session_id)`.
- True when the tenant is enabled, when the session already has a `chat_info` row, or
  when the tenant has fewer than `trial_conversation_limit` distinct `chat_info` sessions
  across its domains.
- Call it in `/chat` before the LLM. Call it in the WhatsApp `handle_text` too, even
  though WhatsApp is locked for disabled tenants (defence in depth).
- When it's false, return `TRIAL_LIMIT_REPLY` as a normal bot response, so the widget
  shows it without error handling.

**Slack:** the summary header links to `DASHBOARD_URL`. Point it at
`https://chatbot0.smalltech.in/dashboard/` (staging: the staging URL +
`/dashboard/`) by setting the **staging** GitHub environment variable. Tell the owner the
production variable needs the same change at release; don't change it yourself.

### Frontend pages (Next, client-rendered behind login)
- `/login/` (with the bootstrap link when needed), `/accept/?token=` (set password),
  `/signup/` (now asks for a password; email required, phone optional).
- `/dashboard/`:
  - Port `zer0-frontend-web/code/src/app/dashboard/*`: table, search, status filter,
    pagination, expandable chat history, remarks, active toggle, summary.
  - Add a domain filter, a channel badge (Web / WhatsApp), and a trial banner ("12 of 20
    trial conversations used. We'll enable your account shortly.").
- `/dashboard/sites/`: list domains with their embed snippet. Add a website. Edit prompts
  (enabled only; disabled tenants see them read-only with a note).
- `/dashboard/whatsapp/`: the tenant's connections, with the same actions as the Phase 1
  admin page (connect, webhook URL + verify token, status, check, replace, test).
  Enabled tenants only.
- `/admin/`: tenants table (enable toggle, trial limit, usage), users (add →
  invite link, reset link), move a domain, all WhatsApp connections. Admin-only; the
  frontend redirects others, and the API enforces it.
- Shared: `src/lib/api.ts`, a fetch wrapper with `credentials: "same-origin"` that
  adds `X-CSRF-Token` and redirects to `/login/` on a 401.

### Slices (in order; commit each)
1. Schema + migration + `auth/` + `/api/auth/*`, with tests: hashing, session_version
   logout-everywhere, CSRF, rate limit, bootstrap only once, token expiry and single use.
2. Tenancy scoping + `/api/leads*` + trial cap in `/chat` and WhatsApp. Tests must prove
   tenant A can never read or patch tenant B's leads.
3. `/api/signup` + `/api/domains` + prompts API. Tests cover duplicates, enabled-only
   edits, and inheritance through the parent domain staying intact.
4. Admin APIs + WhatsApp connection APIs (port from the Jinja admin; then delete
   `admin/` and `templates/admin/`).
5. Lock the legacy endpoints. Tests: 401 without a session, 403 for a non-admin, and the
   admin still works.
6. Frontend: login, accept, signup, dashboard, sites, whatsapp, admin.
7. Docs: README, DEPLOYMENT.md (bootstrap steps, the DASHBOARD_URL change, cutover order
   with zer0-frontend-web), `.env.example`.
8. **Delete this plan.** This file is a temporary work order, not documentation. When
   Phase 3 passes its gate:
   - Move anything still true and useful into README or DEPLOYMENT.md (lasting behaviour,
     setup, operations).
   - Move "Later" items to the PR body.
   - Then `git rm spec/roadmap.md` (and `spec/` if empty) in the last commit.

   If the plan was abandoned partway, note in NOTES.md what didn't work. The owner will
   then switch to spec-driven development (a lasting spec kept in the repo) instead.

**Phase 3 gate:**
- pytest green, including the cross-tenant isolation tests. Frontend build green.
- Local boot with a curl script: bootstrap → login → `/api/auth/me` → create tenant B via
  signup → B's `/api/leads` is empty → B can't PATCH an A lead (403) → B hits the trial
  cap after N `/chat` calls (use a tenant with limit 2 and the LLM stubbed by
  `GROQ_API_KEY=dummy`; the trial reply needs no LLM).
- Staging deploy green. Then bootstrap the staging admin with a strong random password
  from Secret Manager:
  - Store it as a new secret `CHATBOT0_STAGING_ADMIN_LOGIN`, `{"email": ..., "password": ...}`,
    with email `admin@smalltech.in` (Assumed).
  - Never print it. Tell the owner where it is.
- Then run the same curl flow against staging.

---

## Later (not now)
Email sending (invites, resets, lead alerts); Meta Embedded Signup; template-based
WhatsApp outreach; billing and plan enforcement beyond the trial cap; per-tenant Slack
channels.

## Morning hand-off checklist (what the owner must do)
1. Review PR #86 (WhatsApp + restructure + Q + R2 + Phase 3). Merge it when happy; that
   deploys production.
2. Before or at that merge: set the production `DASHBOARD_URL` variable to
   `https://chatbot0.smalltech.in/dashboard/`.
3. After the production deploy serves `/embed.js`, merge the zer0-frontend-web PR.
4. On production: open `/login/` → first-time setup with `CHATBOT0_ADMIN_PASSWORD`.
   That creates your admin account.
