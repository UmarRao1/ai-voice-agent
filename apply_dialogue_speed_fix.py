from pathlib import Path
from datetime import datetime
import re
import shutil
import subprocess
import sys

root = Path.cwd()
agent = root / "backend/app/agent.py"
exporter = root / "backend/app/export_service.py"
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = root / "backups" / f"speed-dialogue-{stamp}"

backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(agent, backup / "agent.py")
shutil.copy2(exporter, backup / "export_service.py")

try:
    a = agent.read_text(encoding="utf-8")
    e = exporter.read_text(encoding="utf-8")

    old = '    caller_turns = []\n    assistant_turns = []'
    new = '    caller_turns = []\n    assistant_turns = []\n    dialogue_turns = []'
    if old not in a:
        raise RuntimeError("Could not find the expected transcript-list block in agent.py")
    a = a.replace(old, new, 1)

    old = '            agent_text = "\\n".join(assistant_turns).strip()[-20000:]'
    new = '''            agent_text = "\\n\\n".join(
                f"{speaker}:\\n{text}"
                for speaker, text in dialogue_turns
            ).strip()[-40000:]'''
    if old not in a:
        raise RuntimeError("Could not find the expected agent_text assignment")
    a = a.replace(old, new, 1)

    old = '''            if role.endswith("user"):
                caller_turns.append(message_text)
            elif role.endswith("assistant"):
                assistant_turns.append(message_text)
            else:
                return'''
    new = '''            if role.endswith("user"):
                caller_turns.append(message_text)
                dialogue_turns.append(("USER", message_text))
            elif role.endswith("assistant"):
                assistant_turns.append(message_text)
                dialogue_turns.append(("ASSISTANT", message_text))
            else:
                return'''
    if old not in a:
        raise RuntimeError("Could not find the expected conversation-role handler")
    a = a.replace(old, new, 1)

    # Give the model clear low-latency behavior without changing its provider.
    old = '"Speak naturally and keep voice responses concise. "'
    new = (
        '"Respond promptly, using one concise sentence when possible. "'
        '"Do not call tools for greetings or ordinary conversation. "'
        '"Use tools only when verified business information is needed. "'
        '"Ask one question at a time. "'
    )
    if old in a:
        a = a.replace(old, new, 1)

    # Export the chronological transcript when available; keep legacy fallback.
    pattern = r'def _transcript_sections\(conversation\):.*?(?=\ndef |\Z)'
    match = re.search(pattern, e, flags=re.S)
    if not match:
        raise RuntimeError("Could not locate _transcript_sections in export_service.py")

    replacement = '''def _transcript_sections(conversation):
    caller_text = getattr(conversation, "caller_text", "") or ""
    agent_text = getattr(conversation, "agent_text", "") or ""

    # New live sessions store the complete ordered dialogue in agent_text.
    if agent_text.lstrip().startswith("USER:") and "ASSISTANT:" in agent_text:
        return [("Transcript", agent_text)]

    # Preserve the export format for older saved conversations.
    return [
        ("USER", caller_text or "No caller transcript was recorded."),
        ("ASSISTANT", agent_text or "No assistant transcript was recorded."),
    ]
'''
    e = e[:match.start()] + replacement + e[match.end():]

    agent.write_text(a, encoding="utf-8")
    exporter.write_text(e, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(agent), str(exporter)],
        cwd=root, capture_output=True, text=True
    )
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout or "Python syntax check failed")

    print("PATCH: PASS")
    print("Syntax verification: PASS")
    print(f"Backup: {backup}")
    print("Changed: backend/app/agent.py")
    print("Changed: backend/app/export_service.py")
    print("Preserved: Deepgram, Edge TTS, LLM provider and existing tool methods")

except Exception as exc:
    shutil.copy2(backup / "agent.py", agent)
    shutil.copy2(backup / "export_service.py", exporter)
    print(f"PATCH FAILED; original files restored. Reason: {exc}")
    sys.exit(1)
