const API_BASE = "http://127.0.0.1:8000";

async function readResponse(response, fallbackMessage) {
  if (!response.ok) {
    let detail = fallbackMessage;

    try {
      const data = await response.json();
      detail = data.detail || detail;
    } catch {
      // Keep the fallback message if the response isn't JSON.
    }

    throw new Error(detail);
  }

  return response.json();
}

export async function checkHealth() {
  const response = await fetch(`${API_BASE}/api/health`);
  return readResponse(response, "Backend health check failed");
}

export async function getConversations() {
  const response = await fetch(`${API_BASE}/api/conversations?limit=50`);
  return readResponse(response, "Could not load conversations");
}

export async function saveConversation(conversation) {
  const response = await fetch(`${API_BASE}/api/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(conversation),
  });

  return readResponse(response, "Could not save conversation");
}

export function getExportUrl(conversationId, format) {
  return `${API_BASE}/api/conversations/${conversationId}/export/${format}`;
}

export async function getLiveKitToken(room, identity) {
  const response = await fetch(`${API_BASE}/api/livekit/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ room, identity }),
  });

  return readResponse(response, "Could not obtain a LiveKit token");
}
