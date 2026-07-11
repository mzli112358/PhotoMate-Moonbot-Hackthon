import { createFileRoute, useNavigate, useRouter } from "@tanstack/react-router";
import { useState } from "react";
import { OptionCard } from "../components/option-card";
import { useVoiceScene } from "../components/voice-context";

export const Route = createFileRoute("/arrival")({
  head: () => ({ meta: [{ title: "已抵达 · 陪伴机器人 R-07" }] }),
  component: ArrivalScreen,
});

function ArrivalScreen() {
  const navigate = useNavigate();
  const router = useRouter();
  const [choice, setChoice] = useState<"start" | "later" | null>(null);
  useVoiceScene({
    state: "listening",
    transcript: "",
    hints: ["好的", "暂时不用"],
  });

  const pick = (value: "start" | "later") => {
    setChoice(value);
    setTimeout(() => {
      if (value === "start") {
        navigate({ to: "/device" });
      } else {
        router.history.back();
      }
    }, 1500);
  };

  return (
    <main className="flex min-h-screen items-stretch pt-24 pb-40">
      <div className="mx-auto flex w-full max-w-[1680px] gap-6 px-8">
        {/* Left sidebar */}
        <aside className="flex w-[280px] shrink-0 flex-col gap-4">
          <div className="rounded-[24px] border border-robot-hairline bg-card p-6 shadow-[0_20px_60px_-40px_rgba(20,15,10,0.4)]">
            <div className="text-[10px] font-semibold tracking-[0.2em] text-robot-orange">
              状态
            </div>
            <h1 className="mt-3 font-display text-[40px] font-medium leading-[1.1] text-robot-ink">
              已抵达
              <span className="text-robot-orange">。</span>
            </h1>
            <p className="mt-3 text-[14px] leading-relaxed text-robot-muted">
              我已到达你身边，随时可以开始拍摄。等你一句话。
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Stat label="距离" value="0.8" unit="米" />
            <Stat label="电量" value="82" unit="%" />
            <Stat label="信号" value="良好" unit="" />
            <Stat label="云台" value="就绪" unit="" />
          </div>

          <div className="flex items-center gap-3 rounded-[20px] border border-robot-hairline bg-card p-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-robot-orange-soft text-base font-semibold text-robot-ink">
              米
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-[10px] font-medium tracking-[0.16em] text-robot-muted">
                接近的对象
              </div>
              <div className="text-[14px] font-semibold text-robot-ink">已识别 · 米卡</div>
            </div>
            <div className="h-2 w-2 rounded-full bg-robot-orange" />
          </div>
        </aside>

        {/* Right: Main content */}
        <section className="flex flex-1 flex-col items-center justify-center">
          <div className="w-full max-w-[1200px] text-center fade-in-up">
            <div className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border border-robot-hairline bg-white/80 px-4 py-1.5 backdrop-blur-sm">
              <span className="h-1.5 w-1.5 rounded-full bg-robot-orange" />
              <span className="text-[11px] font-semibold tracking-[0.22em] text-robot-muted">
                已抵达 · 等待回复
              </span>
            </div>

            <h1 className="font-display text-[72px] font-medium leading-[1.1] tracking-[-0.02em] text-robot-ink">
              <span className="text-robot-orange">PhotoMate</span>已就绪
            </h1>
            <p className="mx-auto mt-5 max-w-xl text-[16px] leading-[1.8] text-robot-muted">
              我就在你身边，只需一句话，我就会按你的想法记录下来。也可以让我先退下。
            </p>

            <div className="mx-auto mt-14 grid max-w-[880px] grid-cols-2 gap-6">
              <OptionCard
                eyebrow="开始拍摄"
                title="好的，开始拍"
                description="我会简单问你几个设置问题。"
                hint="好的"
                selected={choice === "start"}
                dimmed={choice !== null && choice !== "start"}
                onClick={() => pick("start")}
                icon={
                  <svg width="34" height="34" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M4 8h3l2-3h6l2 3h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z"
                      stroke="currentColor"
                      strokeWidth="1.8"
                    />
                    <circle cx="12" cy="13" r="3.5" stroke="currentColor" strokeWidth="1.8" />
                  </svg>
                }
              />
              <OptionCard
                eyebrow="稍后再说"
                title="暂时不用"
                description="我会回到待命状态，随叫随到。"
                hint="暂时不用"
                selected={choice === "later"}
                dimmed={choice !== null && choice !== "later"}
                onClick={() => pick("later")}
                icon={
                  <svg width="34" height="34" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M6 6l12 12M18 6L6 18"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                    />
                  </svg>
                }
              />
            </div>
          </div>
        </section>
      </div>
    </main>
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
