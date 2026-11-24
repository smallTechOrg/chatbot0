# chatbot0

chatbot0 is the AI chat agent for small-business websites, part of [Zer0](https://zer0.smalltech.in) by smallTech. This repository (formerly `Zer0-sales-agent`) is its backend: the chat API behind the embeddable widget, the lead and prompt storage, and the public pages at [chatbot0.smalltech.in](https://chatbot0.smalltech.in). It is a Flask app that calls the LLM through LangChain.

Prompts are stored per domain in the `prompts` table (`base-prompt`, `company`, `intro-message`); a visitor's site is matched to a domain key through the `domains` table. The Cloud Run service, image repository and runtime service account keep their original `zero-sales-agent` names (see `DEPLOYMENT.md`).

## Tech Stack

- [Flask](https://flask.palletsprojects.com/en/stable/) – For backend
- [Langchain](https://python.langchain.com/docs/introduction/) – Framework to build Chatbot

## Features

- Fast, production-ready backend (Flask)
- Modular integration with Groq's LLM via LangChain
- Runs on Windows, Linux, and macOS


## Prerequisites

### Install Python 

   - [Windows](https://github.com/Madhyamakist/workspace-setup-windows) 
   - [macOS](https://github.com/Madhyamakist/workspace-setup-mac/blob/dev/python_installation.md)
   <!-- - [Linux](https://github.com/Madhyamakist/workspace-setup-windows/blob/dev/python_installation.md)   -->


### Python version control

#### macOS and Linux

<details>


The Python version needs to be the same as mentioned in the `.tool-versions` file.

Make sure the correct Python version has been set up using `asdf` before you work on this project.
```
python3 --version
```


</details>

#### Windows

<details>


- The Python version needs to be the same as mentioned in the `.python-version` file using pyenv-win.

- Make sure the correct Python version has been set by running `python --version`


</details>

---
### Get a valid Groq API


- Go to [Groq](https://console.groq.com/keys) and create API Key
- Put your Groq API key in `.env` file

---
### Setup PostgreSQL


- Install and setup PostgreSQL in you local
- Adjust your username and password in `.env` file

## Getting Started

### Clone the repository:

```bash
git clone https://github.com/Madhyamakist/ai-agent-boilerplate.git myproject
```

---

### Set up virtual environment
#### Windows
<details>
- To create a virtual environment called "venv", run

```bash
python -m venv venv
```
-  To activate the environment
```bash
venv\Scripts\activate
```
</details>

#### macOS
<details>

- Create a virtual environment named "venv", 

```bash
python3 -m venv venv
```
-  To activate the environment
```bash
source venv/bin/activate
```
</details>

---

### Install dependencies
After activating your virtual environment, install dependencies by

```bash
pip install -r requirements.txt
```

## Run Flask to render frontend

### Setup Env

Cope `.env.example` into `.env` (gitignored).
```
cp .env.example .env
```

Replace the values (get it from team members?)
```
GROQ_API_KEY=randomstring
DATABASE_URL=postgresql://username:password@localhost:5432/
```


### Run

If virtual environment is activated and dependencies are installed then run chatbot by:

```bash
python app.py
```
Now visit http://127.0.0.1:5000/ in your browser.
For newer APIs visit http://127.0.0.1:5001/api/docs.

## How prompts are chosen (domain hierarchy)

Every website is a row in `domains`; its `parent` column points at another website. The hierarchy is set by people,
never guessed from host names: a new website starts under `COMMON` (the default prompts), and its owner or an admin
can move it. For each prompt the bot needs (sales: `base-prompt`, `company`, `intro-message`, `fetch-contact-info`;
generic: `system`, `fetch-name`) the lookup is:

1. the website's own prompt, if it has one;
2. otherwise its parent's, then the parent's parent, and so on up the whole chain (at most 10 domains; a parent
   loop is cut at the first repeated domain);
3. if no domain in the chain has it, the prompt is empty. `COMMON` is only used when it is in the chain: a domain
   with no parent does not fall back to it by itself.

Each prompt type is resolved separately: a website can have its own `company` text and still inherit `base-prompt`
and `intro-message` from further up, and each one can come from a different ancestor.

**Who sets the parent**

- An enabled account sets the parent of its own websites on Websites (`PUT /api/domains/<key>/parent`,
  body `{"parent_key": "..."}`). The parent must be another website of the same account, or `COMMON`. It can never be
  another account's website, because the child would inherit that company's prompt.
- An admin sets any website's parent to any website on /admin/ (`PUT /api/admin/domains/<key>/parent`).
- Both refuse a website as its own parent, and any change that would make a loop (the check walks up from the
  proposed parent), with a 400 and a message.
- The parent belongs to the key, not to one row: a `www.` address shares its main row's key, so every row with the key
  changes together. Both calls return the new chain, and the prompt-chain view shows it straight away.

The dashboard's Websites page shows, for each website, its lookup order and where every prompt in effect comes from
("own", "inherited from X", "default (COMMON)"); admins can see this for any website on /admin/.
`GET /api/domains/<key>/prompt-chain` returns the same data.

**One-time data migrations.** `core/schema.py` runs each named entry of `DATA_MIGRATIONS` exactly once and records its
name in `data_migrations`, so a restart never undoes a later manual change. The first one,
`2026-11-24-smalltech-subdomains-under-smalltech`, moved the `*.smalltech.in` websites of the smallTech account that
were under `COMMON` to `SMALLTECH` (the `www.smalltech.in` row keeps the SMALLTECH key and is left alone). It logs each
re-parented key and address at INFO.

## Frontend (`frontend/`)

Everything a person sees on chatbot0 (the marketing pages, sign-up, and later the
dashboard) is a Next.js app in `frontend/` (App Router, TypeScript strict,
Tailwind 4), built as a static export. Flask serves the export (`web/`) for any
GET that no API route matched, at the root of every host; `/api/docs` is the
OpenAPI UI and `/api/legacy-docs` the old Swagger UI. `/chatbot0/<page>` 301s
to `/<page>`.

```bash
cd frontend
npm ci
npm run dev        # http://localhost:3001, API calls forwarded to Flask on :5001
npm run build      # writes frontend/out, which Flask serves (FRONTEND_DIR overrides)
npm test           # vitest;  npx tsc --noEmit  and  npm run lint  are CI checks too
```

Plans and industries live in `frontend/src/content/`, page styles in
`frontend/src/styles/site.css`, and all calls to the API in `frontend/src/lib/api.ts`.
The Docker image builds the frontend in a node stage and copies it to `/app/frontend_out`.

## Code layout

```
app.py          create_app(): wires blueprints, database bootstrap, scheduler
web/            serves the Next.js export (frontend/out) for paths no API route matched
frontend/       the Next.js app
core/           config (every env setting), db_pool, schema (table bootstrap), crypto, paths
chat/           the chat engine (engine, history, prompts, prompt_store, lead_capture, contact_validation)
leads/          lead queries and updates (repository)
summary/        periodic summary, Slack messages, scheduler
domains/        domains resource (schemas, service, repository)
whatsapp/       WhatsApp Cloud API (client, formatting, repository, service)
admin/          admin pages (to be replaced by the Next.js app)
api/            HTTP only: parse the request, call the code above, shape the response
test/           pytest suite (needs a local PostgreSQL)
```

## Accounts, tenants and the dashboard

Every customer is a **tenant** (`tenants`), with users who sign in by **email + password** (`users`; scrypt
hashes, a signed session cookie, a CSRF header on every state-changing call). A tenant owns many websites
(`domains.tenant_id`; sub-domains still inherit prompts through `domains.parent`). All domains that existed
before accounts belong to one enabled `smallTech` tenant.

- **Sign-up** (`/signup/`, `POST /api/signup`) creates a tenant that is **not enabled**, its first user and its
  website, and signs in. Until a chatbot0 admin enables the tenant (`/admin/`), the widget answers up to
  `trial_conversation_limit` conversations (default 20) and then replies "This assistant isn't active yet."
  with no LLM call (`tenancy.conversation_allowed`, also checked for WhatsApp). The dashboard shows the leads
  read-only for prompts and WhatsApp; enabled tenants can edit prompts and connect WhatsApp.
- **Pages** (`frontend/`): `/login/`, `/accept/?token=` (invite and reset links), `/dashboard/` (leads),
  `/dashboard/sites/` (embed snippet, prompts, add a website), `/dashboard/whatsapp/`, `/admin/` (admins).
- **No email service yet:** an admin creates invite and reset links on `/admin/` and sends them by hand.
  Links are single use and expire (invites after 7 days, resets after 24 hours).
- **First admin:** while no admin exists, `/login/` shows "First-time setup", which needs
  `CHATBOT0_ADMIN_PASSWORD` once. After that the shared password logs nobody in.
- **API:** `/api/auth/*`, `/api/signup`, `/api/leads*`, `/api/domains*`, `/api/whatsapp/connections*`,
  `/api/admin/*` (see `/api/docs` for the older, documented ones). Code: `auth/`, `tenancy/`, `leads/`,
  `api/`.
- **Legacy endpoints** (`/chat-info*`, `/prompts`, `/prompt`, `/domains*`) stay public until the cutover; set
  `LOCK_LEGACY_API=true` to make them admin-only (see DEPLOYMENT.md).

## WhatsApp

chatbot0 also answers on WhatsApp (Meta Cloud API), with the same prompts,
history, lead capture and Slack summaries as the web widget; WhatsApp chats are
tagged `channel = whatsapp` in `chat_info`. Replies are pull-only: the customer
writes first.

1. Set `CHATBOT0_SECRET_KEY` (and `CHATBOT0_ADMIN_PASSWORD` for the first-admin setup) in `.env`.
2. Sign in at `/login/` and connect a number under WhatsApp (phone number ID, domain,
   access token, app secret).
3. Paste the shown webhook URL and verify token into the Meta app (WhatsApp >
   Configuration), subscribe to `messages`, and message the number.

Code: `whatsapp/` (client, formatting, repository, service),
`api/whatsapp.py` (webhook), `whatsapp/management.py` and `api/whatsapp_connections.py` (the
connection APIs behind the dashboard's WhatsApp page).

## Test Flask APIs 

If flask is rendered successfully, then test APIs by:

```bash
cd test
pytest --html=test_report.html --self-contained-html -v
```


## For Linting

Using ruff (example inside ``)
```
ruff check app.py --fix
```

## Deployment

Pushes to `staging` and `main` deploy to Cloud Run through GitHub Actions.
See [DEPLOYMENT.md](DEPLOYMENT.md).
