import { useMemo, useState } from "react";

import { usePhotoAgent, type AgentSnapshot } from "./photo-agent-bridge";

export type AgentLogKind =
  | "transition"
  | "session"
  | "nav"
  | "sse"
  | "action"
  | "error";

export interface AgentLogEntry {
  id: number;
  at: string;
  kind: AgentLogKind;
  message: string;
  detail?: string;
}

let logSeq = 0;

export function createLogEntry(
  kind: AgentLogKind,
  message: string,
  detail?: string,
): AgentLogEntry {
  return {
    id: ++logSeq,
    at: new Date().toLocaleTimeString("zh-CN", { hour12: false }),
    kind,
    message,
    detail,
  };
}

/** Summarise meaningful snapshot deltas for debugging stuck flows. */
export function describeSnapshotChange(
  prev: AgentSnapshot,
  next: AgentSnapshot,
): string | null {
  const parts: string[] = [];

  if (prev.active !== next.active) {
    parts.push(`active ${prev.active} → ${next.active}`);
  }
  if (prev.state !== next.state) {
    parts.push(`state ${prev.state} → ${next.state}`);
  }
  if (prev.s2_phase !== next.s2_phase) {
    parts.push(`s2_phase ${prev.s2_phase} → ${next.s2_phase}`);
  }
  if (prev.device !== next.device) {
    parts.push(`device ${prev.device ?? "—"} → ${next.device ?? "—"}`);
  }
  if (prev.mode !== next.mode) {
    parts.push(`mode ${prev.mode ?? "—"} → ${next.mode ?? "—"}`);
  }
  if (prev.voice_state !== next.voice_state) {
    parts.push(`voice ${prev.voice_state} → ${next.voice_state}`);
  }
  if (prev.session_id !== next.session_id && next.session_id) {
    parts.push(`session_id=${next.session_id}`);
  }
  if (prev.photo_id !== next.photo_id) {
    parts.push(`photo_id ${prev.photo_id ?? "—"} → ${next.photo_id ?? "—"}`);
  }
  if (prev.error !== next.error && next.error) {
    parts.push(`error=${next.error}`);
  }
  if (prev.transcript !== next.transcript && next.transcript) {
    const t =
      next.transcript.length > 48
        ? `${next.transcript.slice(0, 48)}…`
        : next.transcript;
    parts.push(`spoken="${t}"`);
  }

  return parts.length > 0 ? parts.join(" · ") : null;
}

const KIND_STYLES: Record<AgentLogKind, string> = {
  transition: "text-robot-orange",
  session: "text-emerald-600",
  nav: "text-sky-600",
  sse: "text-robot-muted",
  action: "text-violet-600",
  error: "text-red-500",
};

const KIND_LABELS: Record<AgentLogKind, string> = {
  transition: "状态",
  session: "会话",
  nav: "路由",
  sse: "SSE",
  action: "操作",
  error: "错误",
};

/** Collapsible debug log for state transitions and SSE events. */
export function PhotoAgentStateLog() {
  const { logs, clearLogs } = usePhotoAgent();
  const [open, setOpen] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const reversed = useMemo(() => [...logs].reverse(), [logs]);

  return (
    <div className="pointer-events-auto fixed bottom-8 left-8 z-50 w-[min(420px,calc(100vw-2rem))]">
      <div className="overflow-hidden rounded-2xl border border-robot-hairline bg-white/92 shadow-[0_20px_60px_-30px_rgba(20,15,10,0.45)] backdrop-blur">
        <div className="flex items-center justify-between gap-2 border-b border-robot-hairline/80 px-3 py-2">
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="flex min-w-0 flex-1 items-center gap-2 text-left"
          >
            <span className="h-2 w-2 shrink-0 rounded-full bg-robot-orange" />
            <span className="truncate text-[11px] font-semibold tracking-[0.12em] text-robot-ink">
              状态日志
            </span>
            <span className="text-[10px] text-robot-muted">({logs.length})</span>
          </button>
          <div className="flex shrink-0 items-center gap-1">
            <button
              type="button"
              onClick={clearLogs}
              className="rounded-md px-2 py-1 text-[10px] font-medium text-robot-muted transition hover:bg-robot-orange-soft hover:text-robot-ink"
            >
              清空
            </button>
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              className="rounded-md px-2 py-1 text-[10px] font-medium text-robot-muted transition hover:bg-robot-orange-soft"
            >
              {open ? "收起" : "展开"}
            </button>
          </div>
        </div>

        {open && (
          <div className="max-h-56 overflow-y-auto px-2 py-2 font-mono text-[10px] leading-relaxed">
            {reversed.length === 0 ? (
              <p className="px-1 py-3 text-center text-robot-muted">等待 SSE 事件与状态变化…</p>
            ) : (
              <ul className="space-y-1">
                {reversed.map((entry) => (
                  <li key={entry.id}>
                    <button
                      type="button"
                      onClick={() =>
                        setExpandedId((id) => (id === entry.id ? null : entry.id))
                      }
                      className="w-full rounded-md px-1.5 py-1 text-left transition hover:bg-robot-orange-soft/60"
                    >
                      <span className="text-robot-muted">{entry.at}</span>{" "}
                      <span className={`font-semibold ${KIND_STYLES[entry.kind]}`}>
                        [{KIND_LABELS[entry.kind]}]
                      </span>{" "}
                      <span className="text-robot-ink">{entry.message}</span>
                    </button>
                    {expandedId === entry.id && entry.detail ? (
                      <pre className="mx-1.5 mb-1 whitespace-pre-wrap break-all rounded bg-robot-orange-soft/40 px-2 py-1 text-[9px] text-robot-muted">
                        {entry.detail}
                      </pre>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
