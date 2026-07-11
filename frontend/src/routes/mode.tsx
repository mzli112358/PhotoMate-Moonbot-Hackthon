import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { OptionCard } from "../components/option-card";
import { SectionHeader } from "./device";
import { useVoiceScene } from "../components/voice-context";

export const Route = createFileRoute("/mode")({
  head: () => ({ meta: [{ title: "拍摄模式 · 陪伴机器人 R-07" }] }),
  component: ModeScreen,
});

const PRESETS = [
  { name: "环绕", duration: "8 秒", desc: "围绕你转一圈，人物居中。", path: "orbit" },
  { name: "推近", duration: "5 秒", desc: "缓慢向被摄者推进。", path: "dolly" },
  { name: "揭示", duration: "7 秒", desc: "上升并将全景带入画面。", path: "reveal" },
  { name: "起吊", duration: "6 秒", desc: "自低角度升起至广角。", path: "crane" },
  { name: "跟随", duration: "10 秒", desc: "在你行走时并行跟拍。", path: "follow" },
  { name: "定机位", duration: "5 秒", desc: "锁定三脚架的固定镜头。", path: "static" },
] as const;

type Capture = "photo" | "video" | null;

function ModeScreen() {
  const navigate = useNavigate();
  const [capture, setCapture] = useState<Capture>(null);
  const [preset, setPreset] = useState<string | null>(null);

  useVoiceScene({
    state: capture === null ? "listening" : "responding",
    transcript: capture === null ? "" : capture === "photo" ? "一键拍照。" : "视频拍摄。",
    hints:
      capture === null
        ? ["照片", "视频"]
        : capture === "photo"
        ? ["确认", "改成视频"]
        : ["环绕", "推近", "揭示", "起吊", "跟随", "定机位"],
  });

  const handlePhoto = () => {
    setCapture("photo");
    setPreset(null);
    setTimeout(() => navigate({ to: "/preview" }), 1500);
  };

  const handleVideo = () => {
    setCapture("video");
  };

  const handlePreset = (name: string) => {
    setPreset(name);
    setTimeout(() => navigate({ to: "/preview" }), 1500);
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
              第二步
              <span className="text-robot-orange">。</span>
            </h1>
            <p className="mt-3 text-[14px] leading-relaxed text-robot-muted">
              选择拍摄模式；若是视频，再挑一款电影感运镜。
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Stat label="可选模式" value="2" unit="种" />
            <Stat label="运镜预设" value="6" unit="款" />
            <Stat label="已选设备" value="影石link" unit="" />
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
        <section className="flex flex-1 flex-col justify-start">
          <div className="w-full max-w-[1360px]">
            <SectionHeader
              step="第二步 · 拍摄模式"
              title="拍照还是视频？"
              subtitle="点击卡片或用语音选择模式；若是视频，再挑一款电影感运镜。"
            />

            <div className="mt-10 grid grid-cols-2 gap-6">
              <OptionCard
                eyebrow="即时"
                title="一键拍照"
                description="一张光线到位的照片，三秒倒计时。"
                hint="照片"
                selected={capture === "photo"}
                dimmed={capture !== null && capture !== "photo"}
                onClick={handlePhoto}
                icon={
                  <svg width="36" height="36" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="7" stroke="currentColor" strokeWidth="1.8" />
                    <circle cx="12" cy="12" r="2.5" fill="currentColor" />
                  </svg>
                }
              />
              <OptionCard
                eyebrow="电影感"
                title="视频录制"
                description="我来运镜——从下方挑一款运动方式。"
                hint="视频"
                selected={capture === "video"}
                dimmed={capture !== null && capture !== "video"}
                onClick={handleVideo}
                icon={
                  <svg width="36" height="36" viewBox="0 0 24 24" fill="none">
                    <rect x="3" y="6" width="13" height="12" rx="2" stroke="currentColor" strokeWidth="1.8" />
                    <path d="M16 10l5-3v10l-5-3z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
                  </svg>
                }
              />
            </div>

            {/* Preset row */}
            <div className="mt-10">
              <div className="mb-4 flex items-baseline justify-between">
                <div>
                  <div className="text-[10px] font-semibold tracking-[0.22em] text-robot-orange">
                    运镜预设
                  </div>
                  <div className="mt-1 font-display text-2xl font-medium text-robot-ink">
                    {capture === "video" ? "选择一种运镜方式" : "等待选择拍摄模式"}
                  </div>
                </div>
                <div className="text-[11px] text-robot-muted">
                  {capture === "video"
                    ? "共 6 款 · 点击或说出名称即可选择"
                    : capture === "photo"
                    ? "一键拍照无需运镜"
                    : "选择「视频录制」后解锁"}
                </div>
              </div>

              {capture !== "video" ? (
                <ModePlaceholder capture={capture} />
              ) : (
                <div className="grid grid-cols-6 gap-4 fade-in-up">
                  {PRESETS.map((p) => (
                    <OptionCard
                      key={p.name}
                      compact
                      title={p.name}
                      description={p.desc}
                      hint={p.name}
                      selected={preset === p.name}
                      dimmed={preset !== null && preset !== p.name}
                      onClick={() => handlePreset(p.name)}
                      icon={<PathIcon kind={p.path} />}
                    >
                      <div className="mt-3 text-[10px] font-semibold tracking-[0.18em] text-robot-muted">
                        {p.duration}
                      </div>
                    </OptionCard>
                  ))}
                </div>
              )}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function ModePlaceholder({ capture }: { capture: Capture }) {
  const message =
    capture === "photo"
      ? "已选择「一键拍照」，即将进入取景。"
      : "请先在上方选择拍摄模式，再决定运镜方式。";
  return (
    <div className="grid grid-cols-6 gap-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="relative flex h-[196px] flex-col items-center justify-center rounded-[28px] border border-dashed border-robot-hairline bg-white/40 p-5 text-center"
        >
          <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl border border-dashed border-robot-hairline bg-white/70 text-robot-muted/60">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.5" strokeDasharray="2 3" />
              <path d="M8 12h8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </div>
          {i === 2 || i === 3 ? (
            <div className="text-[11px] leading-[1.7] text-robot-muted/80">
              {i === 2 ? message.split("，")[0] : message.split("，")[1] ?? "运镜待解锁"}
            </div>
          ) : (
            <div className="text-[10px] font-semibold tracking-[0.22em] text-robot-muted/50">
              待解锁
            </div>
          )}
        </div>
      ))}
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

function PathIcon({ kind }: { kind: string }) {
  const stroke = "currentColor";
  return (
    <svg width="44" height="44" viewBox="0 0 44 44" fill="none">
      <circle cx="22" cy="26" r="4" fill={stroke} opacity="0.9" />
      {kind === "orbit" && (
        <ellipse cx="22" cy="26" rx="16" ry="6" stroke={stroke} strokeWidth="1.5" strokeDasharray="2 3" />
      )}
      {kind === "dolly" && (
        <path
          d="M6 26 L34 26"
          stroke={stroke}
          strokeWidth="1.5"
          strokeDasharray="2 3"
          markerEnd="url(#arr)"
        />
      )}
      {kind === "reveal" && (
        <path d="M22 40 Q22 20 38 10" stroke={stroke} strokeWidth="1.5" strokeDasharray="2 3" fill="none" />
      )}
      {kind === "crane" && (
        <path d="M8 34 L22 34 L36 8" stroke={stroke} strokeWidth="1.5" strokeDasharray="2 3" fill="none" />
      )}
      {kind === "follow" && (
        <path d="M6 22 L38 22 M6 30 L38 30" stroke={stroke} strokeWidth="1.5" strokeDasharray="2 3" />
      )}
      {kind === "static" && (
        <rect x="10" y="14" width="24" height="18" rx="2" stroke={stroke} strokeWidth="1.5" fill="none" />
      )}
      <defs>
        <marker id="arr" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 z" fill={stroke} />
        </marker>
      </defs>
    </svg>
  );
}
