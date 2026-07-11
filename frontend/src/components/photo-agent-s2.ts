import type { AgentSnapshot } from "./photo-agent-bridge";

/** Human-readable S2 sub-phase for the kiosk sidebar and debug log. */
export function s2PhaseLabel(phase: AgentSnapshot["s2_phase"]): string {
  switch (phase) {
    case "ask_intent":
      return "等待拍照意愿";
    case "ask_device":
      return "选择拍摄设备";
    case "ask_mode":
      return "选择拍照模式";
    case "done":
      return "设置完成";
    default:
      return phase;
  }
}

/** Heading + blurb for the 寻人/邀请 combined page. */
export function searchPageCopy(snapshot: AgentSnapshot): {
  heading: string;
  blurb: string;
  phaseLabel: string | null;
} {
  if (snapshot.state === "S1") {
    return {
      heading: "寻人中",
      blurb: "正在通过传感器寻找想拍照的人。",
      phaseLabel: null,
    };
  }
  if (snapshot.state === "S2") {
    const phase = s2PhaseLabel(snapshot.s2_phase);
    if (snapshot.s2_phase === "ask_intent") {
      return {
        heading: "邀请中",
        blurb: "已发现你！请回答要不要拍照；确认后我会再问用手机还是 Insta360。",
        phaseLabel: phase,
      };
    }
    return {
      heading: "邀请中",
      blurb: `当前：${phase}。请按语音提示回答，页面会自动切换。`,
      phaseLabel: phase,
    };
  }
  return {
    heading: "寻人中",
    blurb: "正在通过传感器寻找想拍照的人。",
    phaseLabel: null,
  };
}
