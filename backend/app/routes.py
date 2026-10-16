from openai import APIConnectionError, APIStatusError, APITimeoutError

from .llm_service import generate_response
from pathlib import Path
from datetime import timedelta
from uuid import uuid4

from livekit import api
from .config import LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import SessionLocal
from .export_service import create_conversation_exports, export_paths
from .models import Conversation

router = APIRouter(prefix="/api", tags=["Voice Agent"])


async def get_db():
    async with SessionLocal() as session:
        yield session


class ConversationCreate(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    caller_text: str = Field(default="", max_length=20000)
    agent_text: str = Field(default="", max_length=20000)

class AIRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)


class LiveKitTokenRequest(BaseModel):
    room: str = Field(default="voice-agent-demo", min_length=1, max_length=100)
    identity: str | None = Field(default=None, min_length=1, max_length=100)    


@router.post("/livekit/token")
async def create_livekit_token(payload: LiveKitTokenRequest):
    if not all((LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)):
        raise HTTPException(
            status_code=503,
            detail="LiveKit credentials are not configured on the server.",
        )

    identity = payload.identity or f"browser-{uuid4().hex[:12]}"

    try:
        token = (
            api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
            .with_identity(identity)
            .with_ttl(timedelta(minutes=10))
            .with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=payload.room,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=True,
                )
            )
            .to_jwt()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not create a LiveKit access token.",
        ) from exc

    return {
        "server_url": LIVEKIT_URL,
        "token": token,
        "room": payload.room,
        "identity": identity,
    }


@router.get("/health")
async def health():
    return {"status": "ok", "service": "ai-voice-agent"}


@router.post("/conversations")
async def save_conversation(
    payload: ConversationCreate,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.scalar(
        select(Conversation).where(
            Conversation.session_id == payload.session_id
        )
    )

    if existing:
        existing.caller_text = payload.caller_text
        existing.agent_text = payload.agent_text
        await db.commit()
        await db.refresh(existing)
        conversation = existing
    else:
        conversation = Conversation(
            session_id=payload.session_id,
            caller_text=payload.caller_text,
            agent_text=payload.agent_text,
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

    # Generate both files after the conversation has been saved.
    try:
        docx_path, pdf_path = create_conversation_exports(conversation)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Conversation was saved, but export generation failed: {exc}",
        ) from exc

    return {
        "id": conversation.id,
        "session_id": conversation.session_id,
        "caller_text": conversation.caller_text,
        "agent_text": conversation.agent_text,
        "created_at": conversation.created_at,
        "exports": {
            "word": f"/api/conversations/{conversation.id}/export/docx",
            "pdf": f"/api/conversations/{conversation.id}/export/pdf",
            "word_filename": docx_path.name,
            "pdf_filename": pdf_path.name,
        },
    }


@router.get("/conversations")
async def list_conversations(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    if not 1 <= limit <= 100:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 100",
        )

    result = await db.scalars(
        select(Conversation)
        .order_by(Conversation.id.desc())
        .limit(limit)
    )

    return [
        {
            "id": item.id,
            "session_id": item.session_id,
            "caller_text": item.caller_text,
            "agent_text": item.agent_text,
            "created_at": item.created_at,
        }
        for item in result.all()
    ]


@router.get("/conversations/{conversation_id}/export/{file_format}")
async def download_conversation_export(
    conversation_id: int,
    file_format: str,
    db: AsyncSession = Depends(get_db),
):
    if file_format not in {"docx", "pdf"}:
        raise HTTPException(
            status_code=400,
            detail="Unsupported format. Use 'docx' or 'pdf'.",
        )

    conversation = await db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    docx_path, pdf_path = export_paths(conversation)
    file_path: Path = docx_path if file_format == "docx" else pdf_path

    # Re-create a missing file from the saved database transcript.
    if not file_path.is_file():
        docx_path, pdf_path = create_conversation_exports(conversation)
        file_path = docx_path if file_format == "docx" else pdf_path

    media_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if file_format == "docx"
        else "application/pdf"
    )

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=file_path.name,
    )

@router.post("/ai/respond")
async def ai_respond(payload: AIRequest):
    try:
        answer = await generate_response(payload.message)

        return {
            "model": "qwen2.5:3b",
            "caller_text": payload.message,
            "agent_text": answer,
        }

    except APITimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail="The AI model took too long to respond.",
        ) from exc

    except APIConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not connect to Ollama. Check that Ollama is running.",
        ) from exc

    except APIStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail="Ollama returned an API error.",
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc