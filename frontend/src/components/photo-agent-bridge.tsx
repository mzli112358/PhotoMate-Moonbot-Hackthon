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

import {
  createLogEntry,
  describeSnapshotChange,
  type AgentLogEntry,
} from "./photo-agent-log";

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

const MAX_LOG_ENTRIES = 300;

type PhotoAgentContextValue = {
  connected: boolean;
  snapshot: AgentSnapshot;
  logs: AgentLogEntry[];
  appendLog: (entry: AgentLogEntry) => void;
  clearLogs: () => void;
  start: () => Promise<void>;
  stop: () => Promise<void>;
};

const PhotoAgentContext = createContext<PhotoAgentContextValue | null>(null);

const PREVIEW_URL = "/api/photo-agent/session/preview.mjpg";

export function PhotoAgentBridgeProvider({ children }: { children: ReactNode }) {
  const [connected, setConnected] = useState(false);
  const [snapshot, setSnapshot] = useState<AgentSnapshot>(IDLE_SNAPSHOT);
  const [logs, setLogs] = useState<AgentLogEntry[]>([]);
  const esRef = useRef<EventSource | null>(null);
  const snapshotRef = useRef<AgentSnapshot>(IDLE_SNAPSHOT);

  const appendLog = useCallback((entry: AgentLogEntry) => {
    setLogs((prev) => [...prev.slice(-(MAX_LOG_ENTRIES - 1)), entry]);
  }, []);

  const clearLogs = useCallback(() => {
    setLogs([]);
    appendLog(createLogEntry("action", "日志已清空"));
  }, [appendLog]);

  const applySnapshot = useCallback(
    (next: AgentSnapshot, source: string) => {
      const prev = snapshotRef.current;
      const merged = { ...prev, ...next };
      const change = describeSnapshotChange(prev, merged);
      if (change) {
        appendLog(
          createLogEntry("transition", change, `source=${source}`),
        );
      }
      snapshotRef.current = merged;
      setSnapshot(merged);
    },
    [appendLog],
  );

  useEffect(() => {
    let alive = true;
    fetch("/api/photo-agent/session/state")
      .then((res) => (res.ok ? res.json() : null))
      .then((snap: AgentSnapshot | null) => {
        if (alive && snap) {
          applySnapshot(snap, "initial_fetch");
          appendLog(createLogEntry("sse", "已加载初始会话状态"));
        }
      })
      .catch(() => {
        appendLog(createLogEntry("error", "初始状态拉取失败"));
      });
    return () => {
      alive = false;
    };
  }, [applySnapshot, appendLog]);

  useEffect(() => {
    let retryTimer: number | undefined;
    let closedByCleanup = false;

    const connect = () => {
      const es = new EventSource("/api/photo-agent/session/stream");
      esRef.current = es;

      es.onopen = () => {
        setConnected(true);
        appendLog(createLogEntry("sse", "SSE 已连接"));
      };

      es.onmessage = (ev) => {
        try {
          const payload = JSON.parse(ev.data) as Record<string, unknown>;
          const type = String(payload?.type ?? "unknown");

          if (type === "state" && payload.snapshot) {
            applySnapshot(payload.snapshot as AgentSnapshot, "sse_state");
            return;
          }

          if (type === "session_started") {
            const devices = payload.devices as Record<string, string> | undefined;
            appendLog(
              createLogEntry(
                "session",
                "会话已启动",
                devices ? JSON.stringify(devices, null, 2) : undefined,
              ),
            );
            return;
          }

          if (type === "session_stopped") {
            appendLog(createLogEntry("session", "会话已停止"));
            return;
          }

          if (type === "session_error") {
            appendLog(
              createLogEntry(
                "error",
                "会话运行错误",
                String(payload.error ?? "unknown"),
              ),
            );
            return;
          }

          appendLog(
            createLogEntry(
              "sse",
              `事件 ${type}`,
              JSON.stringify(payload, null, 2),
            ),
          );
        } catch {
          appendLog(createLogEntry("error", "SSE 消息解析失败", ev.data));
        }
      };

      es.onerror = () => {
        setConnected(false);
        appendLog(createLogEntry("sse", "SSE 断开，3s 后重连"));
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
  }, [appendLog, applySnapshot]);

  const start = useCallback(async () => {
    appendLog(createLogEntry("action", "请求启动会话"));
    try {
      const res = await fetch("/api/photo-agent/session/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (!res.ok) {
        const text = await res.text();
        appendLog(
          createLogEntry("error", `启动失败 HTTP ${res.status}`, text),
        );
        return;
      }
      const snap = (await res.json()) as AgentSnapshot;
      applySnapshot(snap, "start_response");
      appendLog(createLogEntry("action", "启动请求成功"));
    } catch (err) {
      appendLog(
        createLogEntry(
          "error",
          "启动请求异常",
          err instanceof Error ? err.message : String(err),
        ),
      );
    }
  }, [appendLog, applySnapshot]);

  const stop = useCallback(async () => {
    appendLog(createLogEntry("action", "请求结束会话"));
    try {
      const res = await fetch("/api/photo-agent/session/stop", { method: "POST" });
      if (!res.ok) {
        appendLog(createLogEntry("error", `结束失败 HTTP ${res.status}`));
        return;
      }
      const snap = (await res.json()) as AgentSnapshot;
      applySnapshot(snap, "stop_response");
      appendLog(createLogEntry("action", "结束请求成功"));
    } catch (err) {
      appendLog(
        createLogEntry(
          "error",
          "结束请求异常",
          err instanceof Error ? err.message : String(err),
        ),
      );
    }
  }, [appendLog, applySnapshot]);

  const value = useMemo(
    () => ({ connected, snapshot, logs, appendLog, clearLogs, start, stop }),
    [connected, snapshot, logs, appendLog, clearLogs, start, stop],
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
