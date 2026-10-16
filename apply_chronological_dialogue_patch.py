from pathlib import Path
import re
import shutil
import subprocess
import sys
from datetime import datetime

root = Path.cwd()
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = root / "backups" / f"chronological-dialogue-patch-{stamp}"

files = [
    "backend/app/models.py",
    "backend/app/routes.py",
    "backend/app/agent.py",
    "backend/app/export_service.py",
    "frontend/src/App.jsx",
    "frontend/src/style.css",
]
for name in files:
    p = root / name
    if not p.is_file():
        raise SystemExit(f"STOP: required file missing: {name}")
    dest = backup / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, dest)

# Work in memory first. Nothing is written until all expected edits match.
content = {name: (root / name).read_text(encoding="utf-8-sig")
           for name in files}

# Restore the model's known structure and add ordered dialogue storage.
content["backend/app/models.py"] = '''from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(100), index=True, unique=True
    )
    caller_text: Mapped[str] = mapped_column(Text, default="")
    agent_text: Mapped[str] = mapped_column(Text, default="")
    dialogue: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
'''

# API: backward-compatible dialogue payload plus SQLite migration.
name = "backend/app/routes.py"
s = content[name]
if "import json" not in s:
    s = "import json\n" + s
if "from sqlalchemy import select, text" not in s:
    s = s.replace("from sqlalchemy import select\n",
                  "from sqlalchemy import select, text\n", 1)

old = '''class ConversationCreate(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    caller_text: str = Field(default="", max_length=20000)
    agent_text: str = Field(default="", max_length=20000)
'''
new = '''class ConversationCreate(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    caller_text: str = Field(default="", max_length=20000)
    agent_text: str = Field(default="", max_length=20000)
    dialogue: list[dict[str, str]] = Field(default_factory=list)


async def ensure_dialogue_column(db: AsyncSession):
    # Keep existing SQLite conversation records intact.
    result = await db.execute(text("PRAGMA table_info(conversations)"))
    columns = {row[1] for row in result.fetchall()}
    if "dialogue" not in columns:
        await db.execute(text(
            "ALTER TABLE conversations "
            "ADD COLUMN dialogue TEXT NOT NULL DEFAULT '[]'"
        ))
        await db.commit()


def decode_dialogue(value):
    try:
        turns = json.loads(value or "[]") if isinstance(value, str) else value
        if not isinstance(turns, list):
            return []
        return [
            turn for turn in turns
            if isinstance(turn, dict)
            and turn.get("role") in ("user", "assistant", "caller")
            and isinstance(turn.get("text"), str)
        ]
    except (TypeError, ValueError):
        return []
'''
if old not in s:
    raise SystemExit("STOP: ConversationCreate section did not match.")
s = s.replace(old, new, 1)

s = s.replace(
'''    existing = await db.scalar(
        select(Conversation).where(''',
'''    await ensure_dialogue_column(db)
    existing = await db.scalar(
        select(Conversation).where(''', 1)

s = s.replace(
'''        existing.caller_text = payload.caller_text
        existing.agent_text = payload.agent_text
        await db.commit()''',
'''        existing.caller_text = payload.caller_text
        existing.agent_text = payload.agent_text
        if payload.dialogue:
            existing.dialogue = json.dumps(
                payload.dialogue, ensure_ascii=False
            )
        await db.commit()''', 1)

s = s.replace(
'''            caller_text=payload.caller_text,
            agent_text=payload.agent_text,
        )''',
'''            caller_text=payload.caller_text,
            agent_text=payload.agent_text,
            dialogue=json.dumps(payload.dialogue, ensure_ascii=False),
        )''', 1)

s = s.replace(
'''        "agent_text": conversation.agent_text,
        "created_at": conversation.created_at,''',
'''        "agent_text": conversation.agent_text,
        "dialogue": decode_dialogue(conversation.dialogue),
        "created_at": conversation.created_at,''', 1)

s = s.replace(
'''    result = await db.scalars(
        select(Conversation)''',
'''    await ensure_dialogue_column(db)
    result = await db.scalars(
        select(Conversation)''', 1)

s = s.replace(
'''            "agent_text": item.agent_text,
            "created_at": item.created_at,''',
'''            "agent_text": item.agent_text,
            "dialogue": decode_dialogue(item.dialogue),
            "created_at": item.created_at,''', 1)

s = s.replace(
'''    conversation = await db.get(Conversation, conversation_id)''',
'''    await ensure_dialogue_column(db)
    conversation = await db.get(Conversation, conversation_id)''', 1)

content[name] = s

# Capture turns in the exact order the LiveKit conversation emits them.
name = "backend/app/agent.py"
s = content[name]
s = s.replace(
'''    caller_turns = []
    assistant_turns = []
    transcript_lock = asyncio.Lock()''',
'''    caller_turns = []
    assistant_turns = []
    dialogue_turns = []
    transcript_lock = asyncio.Lock()''', 1)
s = s.replace(
'''                "agent_text": agent_text,
            }''',
'''                "agent_text": agent_text,
                "dialogue": list(dialogue_turns),
            }''', 1)
s = s.replace(
'''            if role.endswith("user"):
                caller_turns.append(message_text)
            elif role.endswith("assistant"):
                assistant_turns.append(message_text)
            else:
                return''',
'''            if role.endswith("user"):
                caller_turns.append(message_text)
                dialogue_turns.append({
                    "role": "user", "text": message_text
                })
            elif role.endswith("assistant"):
                assistant_turns.append(message_text)
                dialogue_turns.append({
                    "role": "assistant", "text": message_text
                })
            else:
                return''', 1)
if "dialogue_turns.append" not in s:
    raise SystemExit("STOP: agent transcript capture section did not match.")
content[name] = s

# Export every turn in sequence, with legacy fallback for old records.
name = "backend/app/export_service.py"
s = content[name]
start = s.index("def _transcript_sections(conversation):")
end = s.index("\ndef create_conversation_exports(conversation):", start)
s = s[:start] + '''def _transcript_sections(conversation):
    raw = getattr(conversation, "dialogue", None)
    if raw:
        import json
        try:
            turns = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError):
            turns = []
        if isinstance(turns, list) and turns:
            sections = []
            for turn in turns:
                if not isinstance(turn, dict):
                    continue
                role = turn.get("role")
                text = turn.get("text")
                if not isinstance(text, str) or not text.strip():
                    continue
                if role in ("user", "caller"):
                    sections.append(("Caller", text.strip()))
                elif role == "assistant":
                    sections.append(("AI Assistant", text.strip()))
            if sections:
                return sections

    caller_text = (conversation.caller_text or "").strip()
    agent_text = (conversation.agent_text or "").strip()
    return [
        ("Caller", caller_text or "No caller transcript was recorded."),
        ("AI Assistant", agent_text or "No assistant transcript was recorded."),
    ]

''' + s[end:]

# Repair the missing PDF loop, or fail safely if its section is unexpected.
needle = '''        Spacer(1, 10),
    ]

    pdf.build(story)'''
replacement = '''        Spacer(1, 10),
    ]

    for speaker, text in _transcript_sections(conversation):
        story.append(KeepTogether([
            Paragraph(escape(speaker), styles["SpeakerHeading"]),
            Paragraph(escape(text).replace("\\\\n", "<br/>"),
                      styles["TranscriptBody"]),
        ]))

    pdf.build(story)'''
if needle not in s:
    raise SystemExit("STOP: PDF story section did not match.")
s = s.replace(needle, replacement, 1)
content[name] = s

# Dashboard: show ordered dialogue, falling back to legacy fields.
name = "frontend/src/App.jsx"
s = content[name]
old = '''                        <p>{item.caller_text || "No caller text saved"}</p>'''
new = '''                        {Array.isArray(item.dialogue) && item.dialogue.length > 0 ? (
                          <div className="saved-dialogue">
                            {item.dialogue.map((turn, index) => {
                              const assistant = turn.role === "assistant";
                              return (
                                <div
                                  className={`saved-turn ${assistant ? "assistant-turn" : "caller-turn"}`}
                                  key={`${index}-${turn.role}`}
                                >
                                  <span>{assistant ? "AI Assistant" : "Caller"}</span>
                                  <p>{turn.text}</p>
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          <>
                            <p>{item.caller_text || "No caller text saved"}</p>
                            {item.agent_text && (
                              <div className="saved-turn assistant-turn">
                                <span>AI Assistant</span>
                                <p>{item.agent_text}</p>
                              </div>
                            )}
                          </>
                        )}'''
if old not in s:
    raise SystemExit("STOP: dashboard transcript paragraph did not match.")
content[name] = s.replace(old, new, 1)

name = "frontend/src/style.css"
s = content[name]
if ".saved-dialogue" not in s:
    s += '''

/* Chronological saved voice dialogue */
.saved-dialogue { display: flex; flex-direction: column; gap: 8px; margin: 8px 0; }
.saved-turn { padding: 8px 10px; border-radius: 8px; min-width: 0; }
.saved-turn span { display: block; font-size: 9px; font-weight: 700; margin-bottom: 4px; }
.saved-turn p { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; }
.caller-turn { background: #242d42; }
.caller-turn span { color: #a9b7d7; }
.assistant-turn { background: #30294a; }
.assistant-turn span { color: #b6a8ff; }
'''
content[name] = s

# Verify required edits before writing any file.
checks = {
    "backend/app/routes.py": [
        "ensure_dialogue_column(db)",
        '"dialogue": decode_dialogue',
        "ADD COLUMN dialogue",
    ],
    "backend/app/agent.py": [
        "dialogue_turns.append",
        '"dialogue": list(dialogue_turns)',
    ],
    "backend/app/export_service.py": [
        "for speaker, text in _transcript_sections(conversation):",
        "json.loads(raw)",
    ],
    "frontend/src/App.jsx": ["item.dialogue.map", "AI Assistant"],
    "frontend/src/style.css": [".saved-dialogue"],
}
for filename, terms in checks.items():
    for term in terms:
        if term not in content[filename]:
            raise SystemExit(f"STOP: verification failed for {filename}: {term}")

for filename, value in content.items():
    (root / filename).write_text(value, encoding="utf-8")

print("PATCH APPLIED")
print(f"Backup: {backup}")
print("Changed: models, API/database migration, LiveKit transcript capture, exports, dashboard, CSS")
