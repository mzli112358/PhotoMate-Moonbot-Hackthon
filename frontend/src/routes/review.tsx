import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useVoiceScene } from "../components/voice-context";
import { useState } from "react";

export const Route = createFileRoute("/review")({
  head: () => ({ meta: [{ title: "拍摄预览 · PhotoMate" }] }),
  component: ReviewScreen,
});

function ReviewScreen() {
  const navigate = useNavigate();
  const [choice, setChoice] = useState<"retake" | "share" | null>(null);

  useVoiceScene({
    state: "listening",
    transcript: "",
    hints: ["再来一张", "文件获取"],
  });

  const pick = (c: "retake" | "share") => {
    if (choice) return;
    setChoice(c);
    setTimeout(() => {
      navigate({ to: c === "retake" ? "/preview" : "/post" });
    }, 1500);
  };

  return (
    <main className="flex min-h-screen items-stretch pt-24 pb-32">
      <div className="mx-auto flex w-full max-w-[1680px] gap-6 px-8">
        {/* Left sidebar */}
        <aside className="flex w-[280px] shrink-0 flex-col gap-4">
          <div className="rounded-[24px] border border-robot-hairline bg-card p-6 shadow-[0_20px_60px_-40px_rgba(20,15,10,0.4)]">
            <div className="text-[10px] font-semibold tracking-[0.2em] text-robot-orange">
              步骤
            </div>
            <h1 className="mt-3 font-display text-[40px] font-medium leading-[1.1] text-robot-ink">
              第三步
              <span className="text-robot-orange">。</span>
            </h1>
            <p className="mt-3 text-[14px] leading-relaxed text-robot-muted">
              拍摄完成。预览影像，选择继续或获取文件。
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Stat label="分辨率" value="5.7K" unit="" />
            <Stat label="时长" value="8" unit="秒" />
            <Stat label="大小" value="184" unit="MB" />
            <Stat label="格式" value="MP4" unit="" />
          </div>

          <div className="rounded-[20px] border border-robot-hairline bg-card p-4">
            <div className="text-[10px] font-semibold tracking-[0.2em] text-robot-muted">
              会话信息
            </div>
            <div className="mt-2 font-mono text-[13px] text-robot-ink">R07-8F2A-24</div>
            <div className="mt-1 text-[11px] text-robot-muted">影石link · 环绕</div>
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
          <div className="w-full max-w-[1200px]">
            <div className="mb-5 text-center">
              <div className="inline-flex items-center gap-2 rounded-full border border-robot-hairline bg-white/80 px-4 py-1.5 backdrop-blur-sm">
                <span className="h-1.5 w-1.5 rounded-full bg-robot-orange" />
                <span className="text-[11px] font-semibold tracking-[0.22em] text-robot-muted">
                  第三步·影像预览
                </span>
              </div>
            </div>

            {/* Photo preview */}
            <div className="relative mx-auto aspect-[16/10] w-full max-w-[820px] overflow-hidden rounded-[28px] border border-robot-hairline bg-robot-ink shadow-[0_30px_80px_-40px_rgba(20,15,10,0.5)]">
              <div
                className="absolute inset-0"
                style={{
                  background:
                    "radial-gradient(120% 80% at 30% 40%, oklch(0.72 0.14 55) 0%, oklch(0.35 0.09 45) 45%, oklch(0.16 0.03 40) 100%)",
                }}
              />
              <svg
                className="absolute inset-0 h-full w-full"
                viewBox="0 0 160 100"
                preserveAspectRatio="xMidYMid slice"
                aria-hidden
              >
                <g fill="oklch(0.1 0.02 40)" opacity="0.6">
                  <ellipse cx="80" cy="100" rx="70" ry="18" />
                  <path d="M60 100 L60 60 Q60 47 80 47 Q100 47 100 60 L100 100 Z" />
                  <circle cx="80" cy="37" r="10" />
                </g>
              </svg>
              <div className="absolute left-5 top-5 rounded-full bg-black/40 px-3 py-1.5 text-[11px] font-semibold tracking-[0.16em] text-white backdrop-blur-md">
                影石link · 5.7K · 8 秒
              </div>
              <div className="absolute right-5 top-5 rounded-full bg-black/40 px-3 py-1.5 font-mono text-[11px] text-white backdrop-blur-md">
                R07-8F2A-24
              </div>
            </div>

            {/* Two compact options */}
            <div className="mx-auto mt-6 grid max-w-[640px] grid-cols-2 gap-4">
              {[
                { key: "retake" as const, label: "再来一张" },
                { key: "share" as const, label: "文件获取" },
              ].map(({ key, label }) => {
                const active = choice === key;
                const dimmed = choice !== null && !active;
                return (
                  <button
                    key={key}
                    onClick={() => pick(key)}
                    disabled={choice !== null}
                    className={`relative flex items-center justify-center rounded-[20px] border px-6 py-4 text-center font-display text-lg font-medium transition-all duration-300 ${
                      active
                        ? "border-robot-orange bg-robot-orange-soft/60 text-robot-ink shadow-[0_20px_50px_-30px_var(--robot-orange-glow)]"
                        : "border-robot-hairline bg-card text-robot-ink shadow-[0_10px_30px_-20px_rgba(20,15,10,0.35)]"
                    } ${dimmed ? "opacity-50" : "opacity-100"} ${
                      choice === null
                        ? "cursor-pointer hover:-translate-y-0.5 hover:border-robot-orange/60 hover:shadow-[0_16px_40px_-30px_var(--robot-orange-glow)]"
                        : ""
                    }`}
                  >
                    {active && (
                      <span className="absolute right-3 top-3 flex h-2 w-2 rounded-full bg-robot-orange" />
                    )}
                    {label}
                  </button>
                );
              })}
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
