import { createFileRoute } from "@tanstack/react-router";
import { useVoiceScene } from "../components/voice-context";

export const Route = createFileRoute("/phone-finish")({
  head: () => ({ meta: [{ title: "手机拍摄完成 · PhotoMate" }] }),
  component: PhoneFinishScreen,
});

function PhoneFinishScreen() {
  useVoiceScene({
    state: "responding",
    transcript: "",
    hints: ["谢谢"],
  });

  return (
    <main className="flex min-h-screen items-center justify-center px-8 pb-28 pt-24">
      <section className="grid w-full max-w-[1180px] grid-cols-[0.95fr_1.05fr] items-center gap-10">
        <div>
          <div className="text-[11px] font-semibold tracking-[0.24em] text-robot-orange">
            拍摄完成
          </div>
          <h1 className="mt-5 font-display text-[56px] font-medium leading-[1.05] text-robot-ink">
            可以取走手机了
            <span className="text-robot-orange">。</span>
          </h1>
          <p className="mt-5 max-w-[520px] text-[16px] leading-relaxed text-robot-muted">
            感谢使用 PhotoMate。请从固定位置取下手机，并检查手机相册中的拍摄结果。
          </p>
        </div>

        <div className="rounded-[32px] border border-robot-hairline bg-card p-8 shadow-[0_28px_90px_-54px_rgba(20,15,10,0.55)]">
          <div className="flex min-h-[420px] flex-col items-center justify-center rounded-[28px] bg-robot-surface px-8 text-center">
            <PhonePickupIllustration />
            <h2 className="mt-8 font-display text-3xl font-medium text-robot-ink">
              拍摄结果已保存在手机中
            </h2>
            <p className="mt-3 max-w-[420px] text-[14px] leading-relaxed text-robot-muted">
              取下手机时请保持平稳，避免碰到支架或周围设备。
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}

function PhonePickupIllustration() {
  return (
    <svg className="h-auto w-full max-w-[420px]" viewBox="0 0 420 260" fill="none" aria-hidden>
      <rect x="92" y="64" width="236" height="108" rx="24" fill="white" stroke="#221f1a" strokeWidth="4" />
      <rect x="116" y="88" width="188" height="60" rx="12" fill="oklch(0.16 0.03 40)" />
      <circle cx="134" cy="118" r="7" fill="var(--robot-orange)" />
      <path d="M178 148 Q210 128 242 148" stroke="white" strokeWidth="4" strokeLinecap="round" opacity="0.85" />
      <circle cx="210" cy="116" r="20" fill="oklch(0.72 0.14 55)" opacity="0.85" />
      <path d="M166 172 L254 172 L284 224 L136 224 Z" fill="oklch(0.9 0.005 80)" />
      <path d="M300 58 C338 40 364 54 370 82 C378 120 332 126 310 100" stroke="var(--robot-orange)" strokeWidth="8" strokeLinecap="round" />
      <path d="M314 96 L296 96 L304 112" stroke="var(--robot-orange)" strokeWidth="8" strokeLinecap="round" strokeLinejoin="round" />
      <text x="210" y="38" textAnchor="middle" fill="#7a6f63" fontSize="18" fontWeight="600">
        取走手机
      </text>
    </svg>
  );
}
