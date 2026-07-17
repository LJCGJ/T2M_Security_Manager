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

> **Project status:** early and actively developed. The interface, security layer,
> and the wiring for all three automation modes are complete. Live end-to-end runs
> depend on an AI backend with enough capacity (see [Requirements](#requirements)).

---

## Features

- **Conversational AI assistant** for planning and writing tests (QA + security focus).
- **Three automation modes**, selectable in the chat:
  - **Screen testing** — a real browser (Playwright via MCP) that the AI drives step
    by step: navigate, click, type, and validate real behavior on dynamic pages.
  - **API testing** — build an HTTP request (method, URL, headers, body) and let the
    AI call it and analyze the response.
  - **Database testing** — connect to a database and let the AI explore the schema and
    run read-only queries (via a database MCP server).
- **Static DOM scan** — a fast, lightweight read of a page's structure, useful for
  security review and simple checks.
- **Multi-AI routing** — Claude (`sk-ant-...`), OpenAI (`sk-...`), or Gemini, chosen
  automatically by the key prefix, with a clear on-screen indicator.
- **Script generation** — the AI can produce reusable test scripts (Robot Framework,
  Python, or SQL) that you can save and run again.
- **Security-first** — API keys and database passwords are encrypted at rest with
  Windows DPAPI; database access defaults to read-only.

---

## How it works

```
+-------------------+       +------------------+       +-----------------------+
|  T2M Desktop App  |       |   Python agent   |       |     MCP servers /     |
|   (C++/CLI, UI)   | ----> |  (agent_mcp.py)  | ----> |     HTTP tool         |
|                   |       |                  |       |  - Playwright (screen)|
|  chat + forms     | stdin |  agentic loop:   |       |  - DBHub (database)   |
|                   | <---- |  AI <-> tools     | <---- |  - native HTTP (API)  |
+-------------------+ stdout+------------------+       +-----------------------+
```

The C++/CLI desktop app collects the request and passes it to a Python agent over
stdin. The agent starts the right MCP server (or uses a native HTTP tool for APIs),
then runs an **agentic loop**: the AI reasons, calls a tool, observes the real result,
and repeats until the task is done — finally returning a report and, when useful, a
test script.

---

## Requirements

- **Windows** (x64)
- **Node.js 18+** — for the MCP servers (`npx` launches Playwright / database servers)
- **Python 3.10+** with: `mcp`, `anthropic`, `google-generativeai`, `openai`, `requests`
- An **API key** for at least one provider (Claude, OpenAI, or Gemini)

> **A note on AI backends:** the automation modes make multiple sequential AI calls.
> Free Gemini keys have low per-minute limits that can interrupt longer runs; a
> Claude or OpenAI key with available credit gives the most reliable experience.

---

## Getting started

1. Clone the repository:
   ```bash
   git clone https://github.com/LJCGJ/T2M_Security_Manager.git
   ```
2. Install Node.js 18+ and the Python dependencies:
   ```bash
   pip install mcp anthropic google-generativeai openai requests
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
3. Read the report in the chat. Ask the AI to generate a script, then save it with
   **Extract & Save Script**.

---

## Roadmap

- [x] Conversational assistant + three automation modes (screen / API / database)
- [x] Multi-AI routing with on-screen indicator
- [x] Encrypted credentials (DPAPI), read-only database default
- [ ] End-to-end validation runs across all modes
- [ ] Oracle and MongoDB support (dedicated MCP servers)
- [ ] Bundled installer (embedded Python + Node)

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
