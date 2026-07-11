import { createFileRoute } from "@tanstack/react-router";

import { LivePreview, usePhotoAgent } from "../components/photo-agent-bridge";

export const Route = createFileRoute("/search")({
  head: () => ({ meta: [{ title: "寻人 · 陪伴机器人 R-07" }] }),
  component: SearchScreen,
});

function SearchScreen() {
  const { snapshot } = usePhotoAgent();
  const asking = snapshot.state === "S2";

  const heading = asking ? "邀请中" : "寻人中";
  const blurb = asking
    ? "我发现了你！要不要我帮你拍一张？"
    : "正在通过传感器寻找想拍照的人。";

  return (
    <main className="flex min-h-screen items-stretch pt-24 pb-40">
      <div className="mx-auto flex w-full max-w-[1680px] gap-6 px-8">
        <aside className="flex w-[280px] shrink-0 flex-col gap-4">
          <div className="rounded-[24px] border border-robot-hairline bg-card p-6 shadow-[0_20px_60px_-40px_rgba(20,15,10,0.4)]">
            <div className="text-[10px] font-semibold tracking-[0.2em] text-robot-orange">
              步骤
            </div>
            <h1 className="mt-3 font-display text-[40px] font-medium leading-[1.1] text-robot-ink">
              {heading}
              <span className="text-robot-orange">。</span>
            </h1>
            <p className="mt-3 text-[14px] leading-relaxed text-robot-muted">{blurb}</p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Stat label="传感器" value="影石link" unit="" />
            <Stat label="追踪" value="固件级" unit="AI" />
            <Stat label="信号" value="良好" unit="" />
            <Stat label="电量" value="82" unit="%" />
          </div>

          <div className="rounded-[20px] border border-robot-hairline bg-card p-4">
            <div className="text-[10px] font-semibold tracking-[0.2em] text-robot-muted">
              会话状态
            </div>
            <div className="mt-2 flex items-center gap-2">
              <span
                className={`h-2 w-2 rounded-full ${
                  snapshot.active ? "bg-robot-orange" : "bg-robot-muted/50"
                }`}
              />
              <span className="text-[13px] font-medium text-robot-ink">
                {snapshot.active ? `运行中 · ${snapshot.state}` : "待机"}
              </span>
            </div>
          </div>
        </aside>

        <section className="flex flex-1 flex-col">
          <div className="relative overflow-hidden rounded-[36px] border border-robot-hairline bg-robot-ink">
            <div className="relative aspect-[16/9] w-full">
              <LivePreview className="absolute inset-0 h-full w-full object-cover" />
              <div className="absolute left-6 top-6 flex items-center gap-2 rounded-full bg-black/40 px-3 py-1.5 text-[11px] font-semibold tracking-[0.16em] text-white backdrop-blur-md">
                <span className="h-1.5 w-1.5 rounded-full bg-robot-orange" />
                实时画面 · {snapshot.state}
              </div>
              <CornerBrackets />
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
        <div className="text-[11px] font-medium tracking-wider text-robot-muted">{unit}</div>
      </div>
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
