# T2M Security Manager

> AI-powered desktop tool for test automation and security testing, built on the Model Context Protocol (MCP).

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078D6.svg)](#)
[![Language: C++/CLI + Python](https://img.shields.io/badge/language-C%2B%2B%2FCLI%20%2B%20Python-orange.svg)](#)

*Read this in other languages: [Português](README.pt.md)*

<!-- SCREENSHOT: main window / chat interface goes here -->

---

## What it is

T2M Security Manager is a **free, open-source Windows desktop tool** that brings
AI-driven test automation and security testing to individual developers and small
QA teams — without the cost of commercial testing suites.

You describe what you want to test in plain language, and an AI agent executes it
live through the **Model Context Protocol (MCP)**: it drives a real browser, queries
a database, or calls an HTTP API — then reports what it found and can generate a
reusable test script.

The project routes across **Claude, Gemini, and OpenAI** — you choose the AI by the
API key you provide.

> **Project status:** all features are built and the interface is fully functional.
> End-to-end validation runs against live targets are still in progress — see the
> [Roadmap](#roadmap).

---

## Features

- **Conversational AI assistant** for planning and writing tests (QA + security focus).
- **Three automation modes**, selectable in the chat:
  - **Screen testing** — a real browser (Playwright via MCP) that the AI drives step
    by step: navigate, click, type, and validate real behavior on dynamic pages.
  - **API testing** — build an HTTP request (method, URL, headers, body) and let the
    AI call it and analyze the response.
  - **Database testing** — the AI explores the schema and runs queries, read-only by
    default.
- **Seven database engines supported:**

  | Engine | How it connects |
  |---|---|
  | PostgreSQL, MySQL, MariaDB, SQLite, SQL Server | DBHub MCP server |
  | Oracle | Official `python-oracledb` driver (thin mode — no Instant Client needed) |
  | MongoDB | Official MongoDB MCP server |

- **Static DOM scan** — a fast, lightweight read of a page's structure, useful for
  security review and simple checks.
- **Multi-AI routing** — Claude (`sk-ant-...`), OpenAI (`sk-...`), Groq (`gsk_...`), or
  Gemini, chosen automatically by the key prefix, with a clear on-screen indicator.
- **OpenAI-compatible endpoints** — one address field in Settings unlocks Groq, Ollama,
  LM Studio, vLLM and OpenRouter with no new code: they all speak the same protocol.
  Useful for testing without burning paid quota, and Ollama runs **locally, with no
  internet** — the only way to demo for a client whose data cannot leave the building.
- **Cost control** — pick the Claude model (Haiku / Sonnet / Opus) and cap the number
  of agent steps per task, so you decide the trade-off between capability and spend.
- **Session history** — save a conversation and reopen it later, formatting intact.
- **HTML reports** — export the test report or the technical log as a styled HTML file.
- **Script library** — generated scripts (Python, Robot Framework, SQL) are saved and
  listed for reuse.
- **Light and dark themes**, applied across every window.
- **Security-first** — API keys and database passwords are encrypted at rest with
  Windows DPAPI; database access defaults to read-only; credentials are stored in the
  user's own profile folder, never inside the program directory.

---

## How it works

```
+-------------------+       +------------------+       +--------------------------+
|  T2M Desktop App  |       |   Python agent   |       |   MCP servers / drivers  |
|   (C++/CLI, UI)   | ----> |  (agente_mcp.py) | ----> |  - Playwright (screen)   |
|                   |       |                  |       |  - DBHub (SQL databases) |
|  chat + forms     | stdin |  agentic loop:   |       |  - MongoDB MCP (official)|
|                   | <---- |  AI <-> tools    | <---- |  - oracledb (Oracle)     |
+-------------------+ stdout+------------------+       |  - native HTTP (API)     |
                                                       +--------------------------+
```

The C++/CLI desktop app collects the request and passes it to a Python agent over
stdin. The agent starts the right MCP server (or uses a native driver for Oracle and
HTTP), then runs an **agentic loop**: the AI reasons, calls a tool, observes the real
result, and repeats until the task is done — finally returning a report and, when
useful, a test script.

---

## Requirements

- **Windows** (x64)
- **Node.js 18+** — for the MCP servers (`npx` launches the Playwright, DBHub and
  MongoDB servers)
- **Python 3.10+**
- An **API key** for at least one provider (Claude, OpenAI, Gemini or Groq) — or none at
  all, if you use a local model through Ollama

> **A note on AI backends:** the automation modes make **one call per step**, so the
> limit that matters is requests per minute, not tokens. Free Gemini keys allow only a
> few per minute, and a 15-step automation ends up queuing. To test without that
> friction see [OpenAI-compatible endpoints](#openai-compatible-endpoints); for serious
> work, a Claude or OpenAI key with available credit gives the most reliable experience.

---

## OpenAI-compatible endpoints

Groq, Ollama, LM Studio, vLLM and OpenRouter all speak **the same protocol as OpenAI** —
only the address changes. That is why there is no "new provider" in the code: there is
the OpenAI route pointing somewhere else, reusing the same tool-calling loop.

Configure it under **Settings → OpenAI-compatible endpoint**. The *Groq* and *Ollama*
buttons fill the address in for you.

| Service | Address | Key | Example model |
|---|---|---|---|
| Groq (cloud, free tier) | `https://api.groq.com/openai/v1` | your `gsk_...` | `llama-3.3-70b-versatile` or `llama-3.1-8b-instant` |
| Ollama (local) | `http://localhost:11434/v1` | any text (e.g. `ollama`) | `qwen2.5:7b` |
| LM Studio (local) | `http://localhost:1234/v1` | any text | whichever model is loaded |

**Groq needs no configuration:** keys starting with `gsk_` are recognised on their own
and already point at the official address. Paste the key, pick a model, done.

**Ollama, step by step:**

```bash
ollama pull qwen2.5:7b     # download the model (once)
ollama serve               # start the local server
```

Then, in Settings, click *Ollama*, type `qwen2.5:7b` in the model field and register any
key. Prefer models that support **tool calling** — without it the automation modes will
not work, only Chat.

> **Two guarantees.** Leave the field empty and nothing changes: existing installs behave
> exactly as before. And even when it is filled in, keys recognised as Claude (`sk-ant-`),
> OpenAI (`sk-`) or Google (`AIza`/`AQ`) are **never** diverted — only keys that match no
> known provider go to the endpoint. Without that rule, one mistyped address would
> silently hijack keys that already worked.

---

## Getting started

### Option A — installer (recommended)

Download the installer from the [Releases](https://github.com/LJCGJ/T2M_Security_Manager/releases)
page and run it. It installs the app and offers to set up the Python libraries and the
test browser automatically.

### Option B — from source

1. Clone the repository:
   ```bash
   git clone https://github.com/LJCGJ/T2M_Security_Manager.git
   ```
2. Install Node.js 18+, then the Python dependencies:
   ```bash
   pip install -r requirements.txt
   npx playwright install chromium
   ```
3. Open the solution in Visual Studio and build in **Release / x64**.
4. Run the app, add your API key, and choose an automation mode.

<!-- SCREENSHOT: automation menu / API form / database form goes here -->

---

## Usage

1. Open the AI assistant window and select your API key (the indicator shows which
   AI it maps to).
2. Pick a mode:
   - **Chat** — talk through your testing strategy.
   - **DOM Scan** — point at a URL for a quick structural read.
   - **Automation** — choose Screen, API, or Database, fill in the details, and
     describe what to validate.
3. Read the report in the chat. Export it as HTML, save the session to continue later,
   or extract the generated script for reuse.

Settings (folders, model, step limits) live under **Configuracoes** on the main window.

---

## Where your data lives

| What | Where |
|---|---|
| API keys, preferences, theme | `%APPDATA%\T2M Security Manager` (encrypted with DPAPI) |
| Reports, sessions, scripts | Folders you choose in Settings (default: `Documents`) |

Nothing is sent anywhere except to the AI provider whose key you supply.

---

## Roadmap

- [x] Conversational assistant + three automation modes (screen / API / database)
- [x] Seven database engines, including Oracle and MongoDB
- [x] Multi-AI routing with on-screen indicator and model selection
- [x] Encrypted credentials (DPAPI), read-only database default
- [x] Session history, HTML reports, script library, light/dark themes
- [x] Windows installer with automatic dependency setup
- [ ] End-to-end validation runs across all automation modes
- [ ] Published release binaries

---

## Contributing

Contributions are welcome. This is an early-stage project, so issues, ideas, and pull
requests all help. Please open an issue to discuss significant changes first.

---

## License

This project is licensed under the **GNU General Public License v3.0** — see the
[LICENSE](LICENSE) file for details. In short: you are free to use, study, and modify
the software, but distributed derivatives must also remain open under the GPL.

---

## Author

**Leonardo Gonzaga** — QA automation engineer.
GitHub: [@LJCGJ](https://github.com/LJCGJ)

*Built as a free resource for the QA and security testing community.*
