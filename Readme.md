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

## chatbot0 public pages

The marketing pages for **chatbot0** (the chat agent this backend powers) are
rendered server-side by the `chatbot0` blueprint (`chatbot0/`), under the
`/chatbot0/` prefix, because `/` is the legacy Swagger UI:

| Path | Page |
|---|---|
| `/chatbot0/` | Landing page |
| `/chatbot0/pricing` | Pricing (plans live in `chatbot0/content.py`) |
| `/chatbot0/robots.txt`, `/chatbot0/sitemap.xml` | SEO files for chatbot0.smalltech.in |
| `/chatbot0/static/...` | CSS, favicons, logo (`static/chatbot0/`) |

Templates are in `templates/chatbot0/`. Links in them are relative, so the
same pages work at the root of chatbot0.smalltech.in once that host is mapped
onto `/chatbot0/`. Canonical and Open Graph URLs always use
https://chatbot0.smalltech.in. The pages take no input and never touch the
database or the LLM.

## Code layout

```
app.py          create_app(): wires blueprints, database bootstrap, scheduler
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

## WhatsApp

chatbot0 also answers on WhatsApp (Meta Cloud API), with the same prompts,
history, lead capture and Slack summaries as the web widget; WhatsApp chats are
tagged `channel = whatsapp` in `chat_info`. Replies are pull-only: the customer
writes first.

1. Set `CHATBOT0_SECRET_KEY` and `CHATBOT0_ADMIN_PASSWORD` in `.env`.
2. Sign in at `/chatbot0/admin/` and connect a number (phone number ID, domain,
   access token, app secret).
3. Paste the shown webhook URL and verify token into the Meta app (WhatsApp >
   Configuration), subscribe to `messages`, and message the number.

Code: `whatsapp/` (client, formatting, repository, service),
`api/whatsapp.py` (webhook), `admin/` (admin pages).

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
