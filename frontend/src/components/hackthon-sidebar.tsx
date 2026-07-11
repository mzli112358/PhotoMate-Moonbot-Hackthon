import { useHackthonBridge, type RobotPose } from "./hackthon-bridge";

function fmtPose(pose?: RobotPose) {
  if (!pose || pose.x == null || pose.y == null) return "-";
  return `(${Number(pose.x).toFixed(2)}, ${Number(pose.y).toFixed(2)}) · ${Number(
    pose.yaw_deg || 0,
  ).toFixed(1)}°`;
}

function fmtCoord(value: unknown) {
  return typeof value === "number" ? value.toFixed(2) : String(value ?? "-");
}

export function HackthonSidebar() {
  const { activeSpotId, connected, goToSpot, logs, status, stopNavigation, waypoints } =
    useHackthonBridge();

  return (
    <aside className="flow-sidebar flex h-[calc(100vh-7.5rem)] w-[336px] shrink-0 flex-col gap-4 overflow-hidden">
      <section className="rounded-[24px] border border-robot-hairline bg-card p-5 shadow-[0_20px_60px_-44px_rgba(20,15,10,0.45)]">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-[10px] font-semibold tracking-[0.2em] text-robot-orange">
              指挥台
            </div>
            <h2 className="mt-2 font-display text-[30px] font-medium leading-tight text-robot-ink">
              准备
              <span className="text-robot-orange">。</span>
            </h2>
          </div>
          <span
            className={`rounded-full px-3 py-1 text-[11px] font-semibold ${
              connected
                ? "bg-robot-orange-soft text-robot-ink"
                : "bg-robot-surface text-robot-muted"
            }`}
          >
            {connected ? "已连接" : "连接中"}
          </span>
        </div>

        <dl className="mt-5 grid grid-cols-[72px_minmax(0,1fr)] gap-x-3 gap-y-2 text-[13px]">
          <dt className="text-robot-muted">模式</dt>
          <dd className="truncate font-medium text-robot-ink">
            {status?.mock ? "演示 (mock)" : "Galbot 真机"}
          </dd>
          <dt className="text-robot-muted">定位</dt>
          <dd className="font-medium text-robot-ink">{status?.localized ? "已定位" : "未定位"}</dd>
          <dt className="text-robot-muted">导航</dt>
          <dd className="truncate font-medium text-robot-ink">
            {status?.navigation_status || "-"}
          </dd>
          <dt className="text-robot-muted">位姿</dt>
          <dd className="font-mono text-[12px] text-robot-ink">{fmtPose(status?.pose)}</dd>
        </dl>
        <p className="mt-3 text-[12px] leading-relaxed text-robot-muted">
          {status?.message || "等待机器人状态更新"}
        </p>
      </section>

      <section className="flex min-h-0 flex-1 flex-col rounded-[24px] border border-robot-hairline bg-card p-5 shadow-[0_20px_60px_-44px_rgba(20,15,10,0.45)]">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-[10px] font-semibold tracking-[0.2em] text-robot-orange">
              点位
            </div>
            <h3 className="mt-1 font-display text-xl font-medium text-robot-ink">
              拍摄航点
            </h3>
          </div>
          <button
            type="button"
            onClick={() => stopNavigation().catch((err) => window.alert(err.message))}
            className="rounded-full border border-robot-hairline bg-white px-3 py-1.5 text-[12px] font-semibold text-robot-ink transition hover:border-robot-orange hover:text-robot-orange"
          >
            停止
          </button>
        </div>

        <div className="mt-4 min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
          {waypoints.map((spot) => {
            const active = spot.id === activeSpotId;
            return (
              <article
                key={spot.id}
                className={`rounded-[18px] border p-3 transition ${
                  active
                    ? "border-robot-orange bg-robot-orange-soft/60"
                    : "border-robot-hairline bg-robot-surface/50"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h4 className="truncate text-[14px] font-semibold text-robot-ink">
                      {spot.name || spot.id}
                    </h4>
                    <p className="mt-1 line-clamp-2 text-[12px] leading-relaxed text-robot-muted">
                      {spot.description || "来自 config/waypoints.yaml"}
                    </p>
                    <div className="mt-2 font-mono text-[11px] text-robot-muted">
                      ({fmtCoord(spot.pose?.[0])}, {fmtCoord(spot.pose?.[1])})
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => goToSpot(spot.id).catch((err) => window.alert(err.message))}
                    className="shrink-0 rounded-full bg-robot-ink px-3 py-1.5 text-[12px] font-semibold text-white transition hover:bg-robot-orange"
                  >
                    前往
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section className="rounded-[24px] border border-robot-hairline bg-card p-5 shadow-[0_20px_60px_-44px_rgba(20,15,10,0.45)]">
        <div className="text-[10px] font-semibold tracking-[0.2em] text-robot-orange">
          日志
        </div>
        <div className="mt-3 max-h-28 space-y-1 overflow-y-auto font-mono text-[11px] leading-relaxed text-robot-muted">
          {logs.length ? logs.map((item) => <div key={item.id}>{item.text}</div>) : "等待连接..."}
        </div>
      </section>
    </aside>
  );
}
