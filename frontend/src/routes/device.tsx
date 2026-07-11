import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { OptionCard } from "../components/option-card";
import { useVoiceScene } from "../components/voice-context";

export const Route = createFileRoute("/device")({
  head: () => ({ meta: [{ title: "选择设备 · 陪伴机器人 R-07" }] }),
  component: DeviceScreen,
});

function DeviceScreen() {
  const navigate = useNavigate();
  const [choice, setChoice] = useState<"phone" | "insta" | null>(null);
  useVoiceScene({
    state: "responding",
    transcript: "我选择影石link相机",
    hints: ["我的手机", "影石link"]
  });

  const pick = (v: "phone" | "insta") => {
    setChoice(v);
    setTimeout(() => navigate({ to: v === "phone" ? "/phone-setup" : "/mode" }), 1500);
  };

  return (
    <main className="flex min-h-screen items-stretch pt-24 pb-40">
      <div className="mx-auto flex w-full max-w-[1680px] gap-6 px-8">
        {/* Left sidebar */}
        <aside className="flex w-[280px] shrink-0 flex-col gap-4">
          <div className="rounded-[24px] border border-robot-hairline bg-card p-6 shadow-[0_20px_60px_-40px_rgba(20,15,10,0.4)]">
            <div className="text-[10px] font-semibold tracking-[0.2em] text-robot-orange">
              步骤
            </div>
            <h1 className="mt-3 font-display text-[40px] font-medium leading-[1.1] text-robot-ink">
              第一步
              <span className="text-robot-orange">。</span>
            </h1>
            <p className="mt-3 text-[14px] leading-relaxed text-robot-muted">
              选择实际按下快门的设备。点击卡片或说出对应指令均可。
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Stat label="可用设备" value="2" unit="台" />
            <Stat label="连接状态" value="良好" unit="" />
            <Stat label="默认设备" value="影石link" unit="" />
            <Stat label="电量" value="82" unit="%" />
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
          <div className="w-full max-w-[1280px]">
            <SectionHeader
              step="第一步 · 拍摄设备"
              title="使用哪台相机？"
              subtitle="选择实际按下快门的设备。点击卡片或说出对应指令均可。"
            />

            <div className="mt-12 grid grid-cols-2 gap-6">
              <OptionCard
                eyebrow="个人设备"
                title="你的手机"
                description="我会通过本地连接触发手机快门，适合自拍与熟悉的构图。"
                hint="我的手机"
                selected={choice === "phone"}
                dimmed={choice !== null && choice !== "phone"}
                onClick={() => pick("phone")}
                icon={<PhoneIcon />}
              >
                <div className="mt-6 flex items-center gap-3 text-[11px] font-medium text-robot-muted">
                  <Chip>iOS · Android</Chip>
                  <Chip>本地配对</Chip>
                </div>
              </OptionCard>

              <OptionCard
                eyebrow="机身硬件"
                title="影石link"
                description="高分辨率 360° 拍摄，配合电影感运镜，我动，你笑。"
                hint="机器人相机"
                selected={choice === "insta"}
                dimmed={choice !== null && choice !== "insta"}
                onClick={() => pick("insta")}
                icon={<Insta360Icon />}
              >
                <div className="mt-6 flex items-center gap-3 text-[11px] font-medium text-robot-muted">
                  <Chip>360° · 5.7K</Chip>
                  <Chip>电影感运镜</Chip>
                  <Chip>实时预览</Chip>
                </div>
              </OptionCard>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

export function SectionHeader({
  step,
  title,
  subtitle,
}: {
  step: string;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="text-center fade-in-up">
      <div className="inline-flex items-center gap-2 rounded-full border border-robot-hairline bg-white/80 px-4 py-1.5 backdrop-blur-sm">
        <span className="h-1.5 w-1.5 rounded-full bg-robot-orange" />
        <span className="text-[11px] font-semibold tracking-[0.22em] text-robot-muted">
          {step}
        </span>
      </div>
      <h1 className="mx-auto mt-6 max-w-3xl font-display text-6xl font-medium leading-[1.15] tracking-[-0.02em] text-robot-ink">
        {title}
      </h1>
      <p className="mx-auto mt-4 max-w-xl text-[15px] leading-[1.8] text-robot-muted">
        {subtitle}
      </p>
    </div>
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

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full border border-robot-hairline bg-white/70 px-2.5 py-1">
      {children}
    </span>
  );
}

function PhoneIcon() {
  return (
    <svg width="38" height="38" viewBox="0 0 24 24" fill="none">
      <rect x="6" y="2" width="12" height="20" rx="3" stroke="currentColor" strokeWidth="1.8" />
      <path d="M10 18h4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function Insta360Icon() {
  return (
    <svg width="42" height="42" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8" />
      <ellipse cx="12" cy="12" rx="9" ry="4" stroke="currentColor" strokeWidth="1.4" opacity="0.6" />
      <circle cx="12" cy="12" r="2.5" fill="currentColor" />
    </svg>
  );
}
