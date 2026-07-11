import { useNavigate, useRouterState } from "@tanstack/react-router";
import { useEffect, useRef } from "react";

import { usePhotoAgent, type AgentSnapshot } from "./photo-agent-bridge";
import { createLogEntry } from "./photo-agent-log";
import { s2PhaseLabel } from "./photo-agent-s2";
import { useVoice } from "./voice-context";

/** Maps the backend FSM state to the flow page the kiosk should show. */
function routeForSnapshot(snap: AgentSnapshot): string | null {
  if (!snap.active) return null;
  switch (snap.state) {
    case "S0":
    case "S1":
      return "/search";
    case "S2":
      if (snap.s2_phase === "ask_device") return "/device";
      if (snap.s2_phase === "ask_mode") return "/mode";
      return "/search";
    case "S3":
      return "/preview";
    case "S5":
      return "/review";
    case "S6":
      return "/post";
    default:
      return null;
  }
}

/**
 * Single source of truth that follows the live session: drives navigation and
 * feeds the shared voice indicator. Renders a small start/stop control so the
 * kiosk can begin a session without the test console.
 */
export function PhotoAgentController() {
  const { snapshot, connected, start, stop, appendLog } = usePhotoAgent();
  const navigate = useNavigate();
  const { set } = useVoice();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const lastPathRef = useRef(pathname);

  useEffect(() => {
    const target = routeForSnapshot(snapshot);
    if (target && target !== pathname) {
      appendLog(
        createLogEntry(
          "nav",
          `路由 ${pathname} → ${target}`,
          `state=${snapshot.state} s2_phase=${snapshot.s2_phase}`,
        ),
      );
      navigate({ to: target });
    }
  }, [snapshot, pathname, navigate, appendLog]);

  useEffect(() => {
    if (!snapshot.active) return;
    set({
      state: snapshot.voice_state,
      transcript: snapshot.transcript ?? "",
      hints: snapshot.hints ?? [],
    });
  }, [snapshot, set]);

  useEffect(() => {
    if (pathname !== lastPathRef.current) {
      lastPathRef.current = pathname;
      appendLog(createLogEntry("nav", `当前页面 ${pathname}`));
    }
  }, [pathname, appendLog]);

  return (
    <div className="pointer-events-auto fixed bottom-8 right-8 z-50 flex items-center gap-3 rounded-full border border-robot-hairline bg-white/90 px-4 py-2 shadow-[0_20px_60px_-30px_rgba(20,15,10,0.5)] backdrop-blur">
      <span
        className={`h-2 w-2 rounded-full ${
          snapshot.active ? "bg-robot-orange" : connected ? "bg-robot-muted/60" : "bg-red-400"
        }`}
      />
      <span className="text-[11px] font-semibold tracking-[0.14em] text-robot-muted">
        {snapshot.active
          ? snapshot.state === "S2"
            ? `会话 · ${snapshot.state} · ${s2PhaseLabel(snapshot.s2_phase)}`
            : `会话 · ${snapshot.state}`
          : connected
            ? "空闲"
            : "未连接"}
      </span>
      {snapshot.active ? (
        <button
          onClick={() => void stop()}
          className="rounded-full bg-robot-ink px-3 py-1 text-[11px] font-semibold text-white transition hover:opacity-90"
        >
          结束会话
        </button>
      ) : (
        <button
          onClick={() => void start()}
          className="rounded-full bg-robot-orange px-3 py-1 text-[11px] font-semibold text-white transition hover:opacity-90"
        >
          开始会话
        </button>
      )}
    </div>
  );
}
