import { useCallback, useEffect, useRef, useState } from "react";
import { Room, RoomEvent, Track } from "livekit-client";
import {
  checkHealth,
  getConversations,
  saveConversation,
  getExportUrl,
  getLiveKitToken,
} from "./api.js";

function formatDate(value) {
  if (!value) return "Date unavailable";

  const normalizedValue =
    typeof value === "string" && !value.endsWith("Z") && !value.includes("+")
      ? `${value}Z`
      : value;

  const date = new Date(normalizedValue);

  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString([], {
        dateStyle: "medium",
        timeStyle: "short",
      });
}

export default function App() {
  const [backendOnline, setBackendOnline] = useState(false);
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [livekitConnected, setLivekitConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState("Not connected");
  const roomRef = useRef(null);
  const remoteAudioRef = useRef(new Set());
  const [savingDemo, setSavingDemo] = useState(false);

  const refreshData = useCallback(async () => {
    setError("");

    try {
      const [health, history] = await Promise.all([
        checkHealth(),
        getConversations(),
      ]);

      setBackendOnline(health.status === "ok");
      setConversations(Array.isArray(history) ? history : [history]);
    } catch (err) {
      setBackendOnline(false);
      setError(err.message || "Cannot reach the backend.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshData();
  }, [refreshData]);

  useEffect(() => {
    return () => {
      const room = roomRef.current;
      roomRef.current = null;

      if (room) {
        void room.disconnect();
      }

      for (const element of remoteAudioRef.current) {
        element.remove();
      }
      remoteAudioRef.current.clear();
    };
  }, []);

  async function connectLiveKit() {
    if (connecting || livekitConnected) return;

    setConnecting(true);
    setError("");
    setVoiceStatus("Requesting connection...");

    let room;

    try {
      const identity = `browser-${crypto.randomUUID().slice(0, 12)}`;
      const session = await getLiveKitToken("voice-agent-demo", identity);

      room = new Room();
      roomRef.current = room;

      room.on(RoomEvent.TrackSubscribed, (track) => {
        if (track.kind !== Track.Kind.Audio) return;

        const element = track.attach();
        element.autoplay = true;
        element.setAttribute("playsinline", "");
        document.body.appendChild(element);
        remoteAudioRef.current.add(element);
      });

      room.on(RoomEvent.TrackUnsubscribed, (track) => {
        for (const element of track.detach()) {
          element.remove();
          remoteAudioRef.current.delete(element);
        }
      });

      room.on(RoomEvent.Disconnected, () => {
        if (roomRef.current !== room) return;

        roomRef.current = null;
        setLivekitConnected(false);
        setConnecting(false);
        setVoiceStatus("Disconnected");

        for (const element of remoteAudioRef.current) {
          element.remove();
        }
        remoteAudioRef.current.clear();
      });

      await room.connect(session.server_url, session.token);
      await room.localParticipant.setMicrophoneEnabled(true);

      setLivekitConnected(true);
      setVoiceStatus("Connected ? microphone enabled");
    } catch (err) {
      if (roomRef.current === room) {
        roomRef.current = null;
      }

      if (room) {
        try {
          await room.disconnect();
        } catch {
          // Preserve the original connection error.
        }
      }

      setLivekitConnected(false);
      setVoiceStatus("Connection failed");
      setError(err.message || "Could not connect to LiveKit.");
    } finally {
      setConnecting(false);
    }
  }

  async function disconnectLiveKit() {
    const room = roomRef.current;

    if (!room) {
      setLivekitConnected(false);
      setVoiceStatus("Disconnected");
      return;
    }

    setVoiceStatus("Disconnecting...");

    try {
      await room.localParticipant.setMicrophoneEnabled(false);
    } catch {
      // Disconnect even if disabling the microphone fails.
    }

    roomRef.current = null;

    try {
      await room.disconnect();
    } finally {
      for (const element of remoteAudioRef.current) {
        element.remove();
      }
      remoteAudioRef.current.clear();

      setLivekitConnected(false);
      setConnecting(false);
      setVoiceStatus("Disconnected");
    }
  }


  async function createDemoConversation() {
    setSavingDemo(true);
    setError("");

    try {
      await saveConversation({
        session_id: `dashboard-demo-${Date.now()}`,
        caller_text: "This is a dashboard test message.",
        agent_text:
          "The backend successfully saved this demo conversation.",
      });

      await refreshData();
    } catch (err) {
      setError(err.message || "Could not save demo conversation.");
    } finally {
      setSavingDemo(false);
    }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">✳</div>
          <div>
            <strong>
              VOICE<span>OS</span>
            </strong>
            <small>AI RECEPTION PLATFORM</small>
          </div>
        </div>

        <div className="nav-label">WORKSPACE</div>
        <div className="nav-item active">
          <span>◫</span> Overview
        </div>
        <div className="nav-item">
          <span>◉</span> Live receptionist{" "}
          <span className="soon">SOON</span>
        </div>
        <div className="nav-item">
          <span>▤</span> Conversations
        </div>
        <div className="nav-item">
          <span>⚙</span> Settings <span className="soon">SOON</span>
        </div>

        <div className="sidebar-bottom">
          <div className="profile-avatar">AI</div>
          <div className="profile-info">
            <strong>Workspace</strong>
            <small>Local development</small>
          </div>
          <span className="profile-menu">···</span>
        </div>
      </aside>

      <section className="main-panel">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <span>/</span> Overview
          </div>

          <div className="topbar-right">
            <span
              className={`status-pill ${
                backendOnline ? "online" : "offline"
              }`}
            >
              <i />
              {backendOnline ? "Backend connected" : "Backend offline"}
            </span>
            <div className="top-avatar">U</div>
          </div>
        </header>

        <div className="content">
          <div className="welcome-row">
            <div>
              <div className="eyebrow">YOUR AI WORKSPACE</div>
              <h1>
                Voice agent <span>overview</span>
              </h1>
              <p className="subtitle">
                Your receptionist workspace, all in one place.
              </p>
            </div>

            <button
              className="secondary-button"
              onClick={refreshData}
            >
              ↻ Refresh data
            </button>
          </div>

          {error && (
            <div className="error-banner">
              <span>Connection issue: {error}</span>
              <button onClick={refreshData}>Retry</button>
            </div>
          )}

          <div className="stats-grid">
            <article className="stat-card">
              <div className="stat-heading">
                Total conversations
                <span className="stat-icon purple">▤</span>
              </div>
              <div className="stat-number">
                {loading ? "—" : conversations.length}
              </div>
              <div className="stat-foot">
                Saved in your local database
              </div>
            </article>

            <article className="stat-card">
              <div className="stat-heading">
                Backend status
                <span className="stat-icon green">⌁</span>
              </div>
              <div
                className={`stat-number small-number ${
                  backendOnline ? "green-text" : "red-text"
                }`}
              >
                {backendOnline ? "Online" : "Offline"}
              </div>
              <div className="stat-foot">FastAPI service</div>
            </article>

            <article className="stat-card">
              <div className="stat-heading">
                Voice session
                <span className="stat-icon blue">◉</span>
              </div>
              <div className="stat-number small-number">
                {livekitConnected ? "Connected" : connecting ? "Connecting" : "Not connected"}
              </div>
              <div className="stat-foot">
                {livekitConnected ? "LiveKit room joined" : "LiveKit voice session"}
              </div>
            </article>
          </div>

          <div className="workspace-grid">
            <article className="panel voice-panel">
              <div className="panel-header">
                <div>
                  <div className="eyebrow">VOICE CONTROL</div>
                  <h2>Receptionist session</h2>
                </div>
                <span className="beta-tag">LIVEKIT</span>
              </div>

              <div className={`orb ${livekitConnected ? "orb-active" : ""}`}>
                <div className="orb-inner">
                  <span>?</span>
                </div>
                <div className="orb-ring ring-one" />
                <div className="orb-ring ring-two" />
              </div>

              <h3>
                {connecting
                  ? "Connecting..."
                  : livekitConnected
                    ? "Voice session connected"
                    : "Ready when you are"}
              </h3>

              <p className="muted centered">
                {voiceStatus}
              </p>

              <button
                className={
                  livekitConnected
                    ? "secondary-button full-button"
                    : "primary-button full-button"
                }
                onClick={livekitConnected ? disconnectLiveKit : connectLiveKit}
                disabled={connecting}
              >
                {connecting
                  ? "Connecting..."
                  : livekitConnected
                    ? "Disconnect session"
                    : "Connect microphone"}
              </button>

              <div className="voice-note">
                <span>?</span>{" "}
                Connecting requests microphone access and joins your LiveKit room.
              </div>
            </article>

            <article className="panel activity-panel">
              <div className="panel-header">
                <div>
                  <div className="eyebrow">RECENT ACTIVITY</div>
                  <h2>Conversation history</h2>
                </div>
                <span className="count-tag">
                  {conversations.length} records
                </span>
              </div>

              {loading ? (
                <div className="empty-state">
                  <div className="loader" />
                  <p>Loading conversations…</p>
                </div>
              ) : conversations.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">▤</div>
                  <strong>No conversations yet</strong>
                  <p>Your saved conversations will appear here.</p>
                </div>
              ) : (
                <div className="conversation-list">
                  {conversations.map((item) => (
                    <div
                      className="conversation-item"
                      key={item.id ?? item.session_id}
                    >
                      <div className="conversation-icon">◉</div>

                      <div className="conversation-copy">
                        <strong>{item.session_id}</strong>
                        <p>{item.caller_text || "No caller text saved"}</p>
                        <small>{formatDate(item.created_at)}</small>
                      </div>

                      <div className="export-actions">
                        <a
                          className="export-link word-link"
                          href={getExportUrl(item.id, "docx")}
                          download
                        >
                          Word
                        </a>

                        <a
                          className="export-link pdf-link"
                          href={getExportUrl(item.id, "pdf")}
                          download
                        >
                          PDF
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="history-actions">
                <button
                  className="secondary-button"
                  onClick={refreshData}
                >
                  Refresh history
                </button>

                <button
                  className="primary-button"
                  disabled={!backendOnline || savingDemo}
                  onClick={createDemoConversation}
                >
                  {savingDemo ? "Saving…" : "+ Test save"}
                </button>
              </div>
            </article>
          </div>

          <div className="bottom-note">
            <span>✳</span>
            <span>
              <strong>Development workspace</strong> — Voice calls are not
              enabled yet. Next, we will connect the real-time voice pipeline.
            </span>
          </div>

          <footer>
            <span>
              VOICEOS <span className="footer-dot">•</span> LOCAL DEVELOPMENT
            </span>
            <span>AI Voice Agent · v0.1.0</span>
          </footer>
        </div>
      </section>
    </main>
  );
}