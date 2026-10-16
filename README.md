# Nexus AI Voice Agent

**A real-time, multilingual AI voice receptionist powered by LiveKit,Deepgram, Ollama, Python, React, and Model Context Protocol (MCP).**

Nexus AI Voice Agent is a voice-based assistant project designed to handle spoken conversations, respond to user requests, and connect AI interactions with application tools. It combines real-time voice infrastructure with a Python backend and a web-based interface.

> **Project status:** Active development. Configuration, integrations, and deployment requirements may vary by environment.

## Overview

The project explores how real-time voice AI, tool calling, and web applications can work together to create a practical digital receptionist.

### Key Features

- **Real-time voice interaction** — LiveKit-based voice sessions.
- **Speech recognition** — Deepgram speech-to-text integration.
- **Speech generation** — Edge TTS integration.
- **AI conversation processing** — LLM-powered response generation.
- **Tool-enabled workflows** — 13 regular application skills and 5 MCP business tools.
- **Modular backend** — Python application with separated services, routes, and tool logic.
- **Web interface** — React and Vite frontend.
- **Conversation recording** — ConversationRecorder integration.
- **Multilingual direction** — Designed to support English, Urdu, Hindi, and Roman Urdu, subject to the configured models and voices.
- **Extensible architecture** — Structured to support additional tools and business workflows.

## Technology Stack

| Area | Technology |
|---|---|
| Backend | Python |
| Voice infrastructure | LiveKit |
| Speech-to-text (STT) | Deepgram |
| Text-to-speech (TTS) | Edge TTS |
| Language model runtime | Ollama |
| Local language model | Qwen 2.5 3B (`qwen2.5:3b`) |
| LLM API compatibility | OpenAI-compatible local endpoint |
| Frontend | React |
| Frontend tooling | Vite |
| Tool integration | Model Context Protocol (MCP) |
| Development environment | Windows, PowerShell, Python virtual environment |

Ollama enables local model inference, reducing reliance on hosted LLM APIs for supported workflows. The application can use the configured local endpoint at `http://localhost:11434/v1`, with `qwen2.5:3b` as the model when selected in the application configuration.


## Architecture


flowchart TD
    A[User / Caller] --> B[React Frontend]
    B --> C[LiveKit Session]
    C --> D[Voice Agent - Python]
    D --> E[Deepgram STT]
    E --> F[LLM Processing]
    F --> G[Ollama]
    G --> H[Qwen 2.5 3B]
    H --> I[Tool Orchestration]
    I --> J[13 Regular Skills]
    I --> K[5 MCP Business Tools]
    I --> L[Edge TTS]
    L --> C


The diagram illustrates the intended high-level design. Exact execution paths depend on the active application configuration.

## Project Structure

```text
ai-voice-agent/
├── backend/
│   ├── app/
│   │   ├── mcp/
│   │   │   └── server.py
│   │   ├── skills/
│   │   │   └── basic.py
│   │   ├── agent.py
│   │   ├── edge_tts_adapter.py
│   │   ├── export_service.py
│   │   ├── llm_service.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── routes.py
│   │   └── tool_runtime.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   ├── main.jsx
│   │   └── style.css
│   ├── index.html
│   ├── package.json
│   └── package-lock.json
├── .gitignore
└── README.md
```

## Getting Started

### Configure Ollama for Local LLM Inference

1. Install [Ollama](https://ollama.com/download) for Windows.
2. Open PowerShell and download the model:

   ```powershell
   ollama pull qwen2.5:3b
   ```

3. Confirm the model is available:

   ```powershell
   ollama list
   ```

4. Check the local API endpoint:

   ```powershell
   Invoke-RestMethod http://localhost:11434/api/tags
   ```

5. Configure the application to use the local OpenAI-compatible endpoint:

   ```text
   Base URL: http://localhost:11434/v1
   Model: qwen2.5:3b
   ```

   Use these settings only when the application's active LLM configuration supports the Ollama-compatible endpoint.

**Note:** Local inference performance depends on available RAM, CPU/GPU resources, model settings, and prompt length.


### Prerequisites

- Python installed on your system
- Node.js and npm
- Git
- A configured LiveKit project
- Valid credentials for the external services enabled in your configuration

### 1. Clone the repository

```bash
git clone https://github.com/UmarRao1/ai-voice-agent.git
cd ai-voice-agent
```

### 2. Set up the Python environment

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the backend dependencies:

```powershell
python -m pip install -r backend/requirements.txt
```

### 3. Configure environment variables

Create a local `.env` file using the variable names expected by the application configuration.

Configure the credentials required for your enabled LiveKit, Deepgram, and language-model integrations.

**Never commit `.env` files, API keys, tokens, or private credentials.** Keep local configuration separate from the source code.

### 4. Start the backend

From the project root:

```powershell
python -m uvicorn app.main:app --reload --app-dir backend
```

### 5. Start the frontend

Open a second PowerShell terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite in your browser.

### 6. Start the voice agent

From the project root, in a separate terminal with the virtual environment activated:

```powershell
python -m backend.app.agent dev
```

The voice session also requires valid LiveKit configuration and the corresponding frontend connection flow.

## Tool Integration

The application includes two categories of tools:

- **Regular application skills:** 13 skills for application-level operations.
- **MCP business tools:** 5 tools exposed through a separate MCP server.

This separation helps keep business capabilities modular and makes the agent easier to extend.

## Security

- Keep credentials in environment variables.
- Never publish API keys or LiveKit secrets.
- Do not commit virtual environments, local databases containing personal information, or generated private transcripts.
- Use appropriate authentication and access controls before exposing the application publicly.
- Review external service quotas, terms, and deployment requirements before production use.

## Current Limitations

This project is under active development. Real-world reliability, multilingual accuracy, response latency, browser compatibility, and production readiness depend on configuration and testing.

A successful local development run does not by itself establish production readiness.

## Future Improvements

- Improve voice response latency and turn-taking.
- Refine the responsive web interface.
- Expand automated tests and error handling.
- Improve observability and conversation analytics.
- Add deployment automation and production configuration.
- Strengthen authentication, privacy, and operational monitoring.

## Author

**Umar Rao**

AI/ML engineering project focused on voice AI, real-time communication, tool-enabled agents, and full-stack application development.

**Repository:** https://github.com/UmarRao1/ai-voice-agent
