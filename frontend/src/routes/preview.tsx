import { createFileRoute } from "@tanstack/react-router";
import { LivePreview } from "../components/photo-agent-bridge";

export const Route = createFileRoute("/preview")({
  head: () => ({ meta: [{ title: "实时取景 · 陪伴机器人 R-07" }] }),
  component: PreviewScreen,
});

export function PreviewScreen() {
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
              取景中
              <span className="text-robot-orange">。</span>
            </h1>
            <p className="mt-3 text-[14px] leading-relaxed text-robot-muted">
              实时画面已就绪。说出指令即可控制拍摄。
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Stat label="感光度" value="400" unit="ISO" />
            <Stat label="快门" value="1/120" unit="s" />
            <Stat label="镜头" value="广角" unit="16mm" />
            <Stat label="被摄者" value="已锁定" unit="" />
          </div>

          <div className="rounded-[20px] border border-robot-hairline bg-card p-4">
            <div className="text-[10px] font-semibold tracking-[0.2em] text-robot-muted">
              设备状态
            </div>
            <div className="mt-2 flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-robot-orange text-[10px] font-bold text-white">
                R7
              </div>
              <div>
                <div className="text-[13px] font-medium text-robot-ink">影石link</div>
                <div className="text-[11px] text-robot-muted">环绕 · 8 秒 · 5.7K</div>
              </div>
            </div>
            <div className="mt-3 flex flex-col gap-1.5">
              <MetricRow label="存储" value="剩余 128 GB" />
              <MetricRow label="码率" value="120 Mbps" />
              <MetricRow label="信号" value="已锁定" active />
            </div>
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
        <section className="flex flex-1 flex-col">
          <div className="relative overflow-hidden rounded-[36px] border border-robot-hairline bg-robot-ink">
            {/* Live Insta360 sensor feed */}
            <div className="relative aspect-[16/9] w-full">
              <LivePreview className="absolute inset-0 h-full w-full object-cover" />

              {/* Rule-of-thirds overlay */}
              <svg
                className="absolute inset-0 h-full w-full"
                viewBox="0 0 160 90"
                preserveAspectRatio="none"
                aria-hidden
              >
                <g stroke="white" strokeWidth="0.15" opacity="0.3">
                  <path d="M53.3 0 V90 M106.6 0 V90 M0 30 H160 M0 60 H160" />
                </g>
              </svg>

              {/* Top-left chip */}
              <div className="absolute left-6 top-6 flex items-center gap-2 rounded-full bg-black/40 px-3 py-1.5 text-[11px] font-semibold tracking-[0.16em] text-white backdrop-blur-md">
                <span className="h-1.5 w-1.5 rounded-full bg-robot-orange" />
                取景中 · 姿态引导
              </div>

              {/* Corner brackets */}
              <CornerBrackets />
            </div>
          </div>

          {/* Under-frame strip */}
          <div className="mt-6 flex items-center justify-between rounded-full border border-robot-hairline bg-card px-6 py-4">
            <div className="flex items-center gap-4">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-robot-orange text-[10px] font-bold text-white">
                R7
              </div>
              <div>
                <div className="text-[11px] font-semibold tracking-[0.18em] text-robot-muted">
                  影石link
                </div>
                <div className="text-[13px] font-medium text-robot-ink">
                  以 0.4 米/秒 环绕被摄者 · 5.7K · H.265
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Metric label="存储" value="剩余 128 GB" />
              <Metric label="码率" value="120 Mbps" />
              <Metric label="信号" value="已锁定" active />
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

function Metric({ label, value, active = false }: { label: string; value: string; active?: boolean }) {
  return (
    <div className="flex items-center gap-2 rounded-full border border-robot-hairline px-3 py-1.5">
      <span className={`h-1.5 w-1.5 rounded-full ${active ? "bg-robot-orange" : "bg-robot-muted/50"}`} />
      <span className="text-[10px] font-semibold tracking-[0.18em] text-robot-muted">
        {label}
      </span>
      <span className="text-[11px] font-medium text-robot-ink">{value}</span>
    </div>
  );
}

function MetricRow({ label, value, active = false }: { label: string; value: string; active?: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className={`h-1.5 w-1.5 rounded-full ${active ? "bg-robot-orange" : "bg-robot-muted/50"}`} />
        <span className="text-[10px] font-semibold tracking-[0.18em] text-robot-muted">{label}</span>
      </div>
      <span className="text-[11px] font-medium text-robot-ink">{value}</span>
    </div>
  );
}

function CornerBrackets() {
  const cls = "absolute h-6 w-6 border-white/70";
  return (
    <>
      <span className={`${cls} left-3 top-3 border-l border-t`} />
      <span className={`${cls} right-3 top-3 border-r border-t`} />
      <span className={`${cls} left-3 bottom-3 border-l border-b`} />
      <span className={`${cls} right-3 bottom-3 border-r border-b`} />
    </>
  );
}
