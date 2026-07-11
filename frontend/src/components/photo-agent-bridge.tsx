import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

export type AgentState = "S0" | "S1" | "S2" | "S3" | "S5" | "S6";
export type VoiceState = "idle" | "listening" | "processing" | "responding";

export interface AgentSnapshot {
  active: boolean;
  state: AgentState;
  s2_phase: "ask_intent" | "ask_device" | "ask_mode" | "done";
  device: "phone" | "insta" | null;
  mode: "photo" | "video" | null;
  photo_id: string | null;
  photo_url: string | null;
  download_url: string | null;
  qr_url: string | null;
  transcript: string;
  hints: string[];
  voice_state: VoiceState;
  session_id: string | null;
  error: string | null;
  devices: Record<string, string>;
}

const IDLE_SNAPSHOT: AgentSnapshot = {
  active: false,
  state: "S0",
  s2_phase: "ask_intent",
  device: null,
  mode: null,
  photo_id: null,
  photo_url: null,
  download_url: null,
  qr_url: null,
  transcript: "",
  hints: [],
  voice_state: "idle",
  session_id: null,
  error: null,
  devices: {},
};

type PhotoAgentContextValue = {
  connected: boolean;
  snapshot: AgentSnapshot;
  start: () => Promise<void>;
  stop: () => Promise<void>;
};

const PhotoAgentContext = createContext<PhotoAgentContextValue | null>(null);

const PREVIEW_URL = "/api/photo-agent/session/preview.mjpg";

export function PhotoAgentBridgeProvider({ children }: { children: ReactNode }) {
  const [connected, setConnected] = useState(false);
  const [snapshot, setSnapshot] = useState<AgentSnapshot>(IDLE_SNAPSHOT);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    let alive = true;
    fetch("/api/photo-agent/session/state")
      .then((res) => (res.ok ? res.json() : null))
      .then((snap: AgentSnapshot | null) => {
        if (alive && snap) setSnapshot((prev) => ({ ...prev, ...snap }));
      })
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    let retryTimer: number | undefined;
    let closedByCleanup = false;

    const connect = () => {
      const es = new EventSource("/api/photo-agent/session/stream");
      esRef.current = es;

      es.onopen = () => setConnected(true);

      es.onmessage = (ev) => {
        try {
          const payload = JSON.parse(ev.data);
          if (payload?.type === "state" && payload.snapshot) {
            setSnapshot((prev) => ({ ...prev, ...payload.snapshot }));
          }
        } catch {
          // Ignore malformed frames during dev restarts.
        }
      };

      es.onerror = () => {
        setConnected(false);
        es.close();
        if (!closedByCleanup) {
          retryTimer = window.setTimeout(connect, 3000);
        }
      };
    };

    connect();

    return () => {
      closedByCleanup = true;
      if (retryTimer) window.clearTimeout(retryTimer);
      esRef.current?.close();
    };
  }, []);

  const start = useCallback(async () => {
    await fetch("/api/photo-agent/session/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
  }, []);

  const stop = useCallback(async () => {
    await fetch("/api/photo-agent/session/stop", { method: "POST" });
  }, []);

  const value = useMemo(
    () => ({ connected, snapshot, start, stop }),
    [connected, snapshot, start, stop],
  );

  return (
    <PhotoAgentContext.Provider value={value}>{children}</PhotoAgentContext.Provider>
  );
}

export function usePhotoAgent() {
  const value = useContext(PhotoAgentContext);
  if (!value) {
    throw new Error("usePhotoAgent must be used inside PhotoAgentBridgeProvider");
  }
  return value;
}

/** Live sensor preview (MJPEG) shared by the 寻人 and 取景 pages. */
export function LivePreview({ className }: { className?: string }) {
  return (
    <img
      src={PREVIEW_URL}
      alt="实时画面"
      className={className ?? "h-full w-full object-cover"}
    />
  );
}
