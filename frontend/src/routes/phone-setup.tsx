import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { SectionHeader } from "./device";
import { useVoiceScene } from "../components/voice-context";

export const Route = createFileRoute("/phone-setup")({
  head: () => ({ meta: [{ title: "手机准备 · PhotoMate" }] }),
  component: PhoneSetupScreen,
});

function PhoneSetupScreen() {
  const navigate = useNavigate();

  useVoiceScene({
    state: "listening",
    transcript: "",
    hints: ["准备好了"],
  });

  return (
    <main className="flex min-h-screen items-stretch pb-28 pt-24">
      <div className="mx-auto flex w-full max-w-[1680px] gap-6 px-8">
        <aside className="flex w-[280px] shrink-0 flex-col gap-4">
          <div className="rounded-[24px] border border-robot-hairline bg-card p-6 shadow-[0_20px_60px_-40px_rgba(20,15,10,0.4)]">
            <div className="text-[10px] font-semibold tracking-[0.2em] text-robot-orange">
              手机准备
            </div>
            <h1 className="mt-3 font-display text-[40px] font-medium leading-[1.1] text-robot-ink">
              放置手机
              <span className="text-robot-orange">。</span>
            </h1>
            <p className="mt-3 text-[14px] leading-relaxed text-robot-muted">
              把手机固定在拍摄位，并提前打开相机。完成后说“准备好了”或点击语音指令按钮。
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Stat label="设备" value="手机" unit="" />
            <Stat label="方向" value="横屏" unit="" />
            <Stat label="比例" value="16:9" unit="" />
            <Stat label="模式" value="照片" unit="" />
          </div>
        </aside>

        <section className="flex min-w-0 flex-1 flex-col items-center">
          <div className="w-full max-w-[1180px]">
            <SectionHeader
              step="手机拍摄准备"
              title="放好手机，并预设拍摄模式"
              subtitle="请按下面两步完成手机准备。PhotoMate 会在你确认后进入取景。"
            />

            <div className="mt-10 grid grid-cols-[1.05fr_0.95fr] gap-6">
              <div className="rounded-[28px] border border-robot-hairline bg-card p-6 shadow-[0_20px_60px_-44px_rgba(20,15,10,0.35)]">
                <div className="text-[10px] font-semibold tracking-[0.2em] text-robot-orange">
                  01 · 放置
                </div>
                <div className="mt-5 flex min-h-[330px] items-center justify-center rounded-[24px] bg-robot-surface">
                  <PhonePlacementIllustration />
                </div>
                <h2 className="mt-5 font-display text-2xl font-medium text-robot-ink">
                  手机横放，镜头朝向被拍摄者
                </h2>
                <p className="mt-2 text-[14px] leading-relaxed text-robot-muted">
                  确保手机稳定、画面无遮挡，人物位于画面中央附近。
                </p>
              </div>

              <div className="rounded-[28px] border border-robot-hairline bg-card p-6 shadow-[0_20px_60px_-44px_rgba(20,15,10,0.35)]">
                <div className="text-[10px] font-semibold tracking-[0.2em] text-robot-orange">
                  02 · 预设
                </div>
                <div className="mt-5 space-y-3">
                  <GuideRow title="打开相机 App" detail="使用系统相机或已连接的拍摄 App。" />
                  <GuideRow title="选择照片或视频" detail="先确认你想要的拍摄模式。" />
                  <GuideRow title="设置 16:9 横屏画幅" detail="保证后续取景框和前端画面一致。" />
                  <GuideRow title="锁定曝光与焦点" detail="减少机器人移动时的画面闪烁。" />
                </div>
                <button
                  type="button"
                  onClick={() => navigate({ to: "/phone-countdown" })}
                  className="mt-6 w-full rounded-[20px] border border-robot-hairline bg-robot-orange-soft/40 p-4 text-left transition hover:border-robot-orange hover:bg-robot-orange-soft focus:outline-none focus-visible:ring-2 focus-visible:ring-robot-orange"
                >
                  <div className="text-[11px] font-semibold tracking-[0.18em] text-robot-muted">
                    语音指令
                  </div>
                  <div className="mt-2 font-display text-2xl font-medium text-robot-ink">
                    “准备好了”
                  </div>
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function GuideRow({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="flex gap-3 rounded-[18px] border border-robot-hairline bg-robot-surface/60 p-4">
      <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-robot-orange" />
      <div>
        <div className="text-[14px] font-semibold text-robot-ink">{title}</div>
        <div className="mt-1 text-[12px] leading-relaxed text-robot-muted">{detail}</div>
      </div>
    </div>
  );
}

function PhonePlacementIllustration() {
  return (
    <svg className="h-full max-h-[300px] w-full max-w-[520px]" viewBox="0 0 520 300" fill="none">
      <rect x="62" y="82" width="396" height="150" rx="28" fill="white" stroke="#221f1a" strokeWidth="4" />
      <rect x="94" y="108" width="332" height="96" rx="16" fill="oklch(0.16 0.03 40)" />
      <path d="M205 204 L315 204 L350 258 L170 258 Z" fill="oklch(0.9 0.005 80)" />
      <circle cx="116" cy="157" r="10" fill="var(--robot-orange)" />
      <path d="M198 157 H322 M260 105 V208" stroke="white" strokeWidth="1.5" opacity="0.45" />
      <circle cx="260" cy="156" r="28" fill="oklch(0.72 0.14 55)" opacity="0.85" />
      <path d="M230 196 Q260 174 290 196" stroke="white" strokeWidth="4" strokeLinecap="round" opacity="0.85" />
      <path d="M130 58 H390" stroke="var(--robot-orange)" strokeWidth="3" strokeLinecap="round" strokeDasharray="8 10" />
      <text x="260" y="42" textAnchor="middle" fill="#7a6f63" fontSize="18" fontWeight="600">
        16:9 横屏取景
      </text>
    </svg>
  );
}

function Stat({ label, value, unit }: { label: string; value: string; unit: string }) {
  return (
    <div className="rounded-[18px] border border-robot-hairline bg-card p-4">
      <div className="text-[10px] font-semibold tracking-[0.16em] text-robot-muted">
        {label}
      </div>
      <div className="mt-1.5 flex items-baseline gap-1.5">
        <div className="font-display text-2xl font-medium text-robot-ink">{value}</div>
        <div className="text-[11px] font-medium tracking-wider text-robot-muted">
          {unit}
        </div>
      </div>
    </div>
  );
}
