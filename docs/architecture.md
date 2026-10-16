# AI Voice Agent — Architecture

## 1. Overview

AI Voice Agent is a real-time voice receptionist project built with LiveKit Agents, FastAPI, React, Deepgram speech recognition, Edge TTS, an OpenAI-compatible language model interface, and Model Context Protocol (MCP) tools.

The current configuration uses demonstration medical-clinic information. Real business details, appointment availability, and production integrations must be verified before deployment.

## 2. System Architecture

```text
                 CALLER
                   |
                   v
          React Frontend
       (LiveKit Web Client)
                   |
                   v
             LiveKit Room
                   |
                   v
          LiveKit Voice Agent
          backend/app/agent.py
                   |
         +---------+----------+
         |         |           |
         v         v           v
      Deepgram    LLM       Tool Runtime
        STT      Client    tool_runtime.py
         |         |           |
         |         |      +----+----+
         |         |      |         |
         |         |      v         v
         |         |   Python     MCP Server
         |         |   Skills     mcp/server.py
         |         |
         |         v
         |    Generated Text
         |         |
         |         v
         |      Edge TTS
         |   edge_tts_adapter.py
         |         |
         |         v
         |     Audio Frames
         |         |
         +---------+
                   |
                   v
            LiveKit Room
                   |
                   v
          Caller Hears Response


          FastAPI Backend
          backend/app/main.py
                   |
                   v
              API Routes
                   |
                   v
            SQLite Database
        Conversations and Records
```

## 3. Main Components

| Component | Responsibility |
|---|---|
| `backend/app/agent.py` | Defines the LiveKit voice agent, speech and language model configuration, receptionist instructions, registered tools, and live transcript capture. |
| `backend/app/edge_tts_adapter.py` | Uses Edge TTS to generate speech and converts returned MP3 audio into PCM audio frames for LiveKit. |
| `backend/app/tool_runtime.py` | Validates tool arguments and dispatches explicitly registered Python skills and MCP calls. |
| `backend/app/skills/basic.py` | Contains basic Python skills, including greetings and demonstration business information. |
| `backend/app/mcp/server.py` | Defines the MCP server and the tools it exposes. |
| `backend/app/config.py` | Loads application configuration and environment variables. |
| `backend/app/llm_service.py` | Provides a separate language-model response and tool-calling flow. |
| `backend/app/main.py` | Creates the FastAPI application and manages database startup and shutdown. |
| `backend/app/routes.py` | Defines HTTP API routes used by the frontend and conversation features. |
| `backend/app/database.py` | Provides database initialization and connection management. |
| `backend/app/models.py` | Defines database models. |
| `frontend/src/App.jsx` | Contains the main React interface. |
| `frontend/src/api.js` | Provides frontend API helpers. |
| `frontend/src/main.jsx` | Starts the React application. |
| `frontend/src/style.css` | Defines frontend styling. |

## 4. Voice Conversation Lifecycle

1. The frontend requests the necessary LiveKit connection information from the backend.
2. The frontend connects to a LiveKit room and enables the caller's microphone.
3. The LiveKit agent joins the room and receives caller audio.
4. Deepgram Speech-to-Text (STT) converts speech into text.
5. The language model interprets the request and generates a response.
6. When needed, the model requests a registered tool.
7. The tool runtime validates the arguments and dispatches the supported operation.
8. Edge TTS generates speech audio, which the adapter decodes into PCM frames.
9. LiveKit delivers the audio response to the caller.
10. Completed conversation items can be captured and sent to the backend for persistence.

## 5. Python Skills and MCP

Python skills and MCP tools provide a controlled way for the assistant to retrieve information or perform supported operations.

The tool runtime should only execute explicitly registered tools. Tool arguments must be validated, and failed operations must not be described as successful.

The available tool inventory should be verified against the current source code rather than assumed from older project notes.

## 6. Language Model Configuration

The voice agent uses an OpenAI-compatible client interface configured through environment variables. The current configuration supports an Ollama endpoint and a configurable model name.

Local model performance depends on the model, hardware, memory, and inference configuration. A model endpoint being configured does not guarantee that the model is running or responding successfully.

## 7. Conversation Persistence

The voice agent captures completed conversation items and sends transcript information to the local FastAPI backend.

The backend provides API routes and database integration for application records and conversation persistence. Persistence failures should be logged and investigated rather than silently treated as successful saves.

## 8. Safety and Limitations

- Do not commit API keys, passwords, tokens, or the real `.env` file.
- Use `.env.example` to document required configuration with placeholders only.
- Treat demonstration business information as sample data.
- Schedule validation is not proof that a database appointment slot is available.
- The current agent instructions state that appointment booking is not enabled.
- Do not claim an appointment has been booked unless a verified booking operation actually succeeds.
- Configure authentication, logging, privacy protections, and production infrastructure before public deployment.

## 9. Local Development

Run the FastAPI backend from the project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir backend
```

Run the LiveKit agent from the project root:

```powershell
.\.venv\Scripts\python.exe -m backend.app.agent dev
```

Run the frontend in a separate terminal:

```powershell
Set-Location "D:\Projects\ai-voice-agent\frontend"
npm install
npm run dev
```

The frontend development server normally runs at `http://localhost:5173`.

The FastAPI API is available at `http://127.0.0.1:8000`, with interactive API documentation at `http://127.0.0.1:8000/docs`.

## 10. Project Status

This repository is a development project. The voice pipeline, tool integrations, database behavior, and deployment configuration should be tested in the target environment before production use.