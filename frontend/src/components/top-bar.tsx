import { Link, useRouterState } from "@tanstack/react-router";

const STEPS = [
  { to: "/", label: "准备" },
  { to: "/arrival", label: "抵达" },
  { to: "/device", label: "设备" },
  { to: "/mode", label: "模式" },
  { to: "/preview", label: "取景" },
  { to: "/review", label: "预览" },
  { to: "/post", label: "分享" },
] as const;

export function TopBar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const activeIdx = STEPS.findIndex((s) => s.to === pathname);
  const isInFlow = activeIdx >= 0;
  const safeIdx = Math.max(0, activeIdx);
  const progress = STEPS.length > 1 ? safeIdx / (STEPS.length - 1) : 0;

  return (
    <header className="fixed inset-x-0 top-0 z-40 flex items-center justify-between gap-8 px-8 pt-6">
      {/* PhotoMate Logo */}
      <div className="flex shrink-0 items-center gap-3">
        <svg width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
          {/* Outer ring - black */}
          <circle cx="18" cy="18" r="17" stroke="#0F172A" strokeWidth="2.5" />
          {/* Inner lens - white with orange accent */}
          <circle cx="18" cy="18" r="11" fill="white" stroke="#0F172A" strokeWidth="1.5" />
          {/* Aperture blade 1 */}
          <path d="M18 12.5C21.5 12.5 24.2 15.2 24.2 18.7" stroke="#0F172A" strokeWidth="1.2" strokeLinecap="round" />
          {/* Aperture blade 2 */}
          <path d="M24.2 18.7C24.2 22.2 21.5 24.9 18 24.9" stroke="#0F172A" strokeWidth="1.2" strokeLinecap="round" />
          {/* Aperture blade 3 */}
          <path d="M18 24.9C14.5 24.9 11.8 22.2 11.8 18.7" stroke="#0F172A" strokeWidth="1.2" strokeLinecap="round" />
          {/* Orange dot accent */}
          <circle cx="18" cy="18" r="3.5" fill="#FF5A1F" />
          {/* Small highlight */}
          <circle cx="20" cy="16" r="1" fill="white" />
        </svg>
        <div className="leading-tight">
          <div className="text-[15px] font-bold tracking-[0.04em] text-robot-ink">
            PhotoMate
          </div>
          <div className="text-[11px] font-medium tracking-[0.1em] text-robot-muted">
            智能摄影师解决方案
          </div>
        </div>
      </div>

      {/* Progress bar + dots */}
      {isInFlow && (
        <nav className="flex min-w-0 flex-1 items-center justify-center">
          <div className="relative w-full max-w-[720px] px-4 pb-7 pt-1">
            {/* Track (aligned with dot centers) */}
            <div className="absolute inset-x-4 top-[17px] h-[2px] rounded-full bg-robot-hairline" />
            {/* Fill */}
            <div
              className="absolute left-4 top-[17px] h-[2px] rounded-full bg-robot-orange transition-all duration-500"
              style={{ width: `calc((100% - 2rem) * ${progress})` }}
            />
            {/* Dots row */}
            <ol className="relative flex w-full items-center justify-between">
              {STEPS.map((step, i) => {
                const isActive = i === activeIdx;
                const isDone = i < activeIdx;
                return (
                  <li key={step.to} className="relative flex flex-col items-center">
                    <Link to={step.to} className="group flex flex-col items-center">
                      <span
                        className={`flex h-[34px] w-[34px] items-center justify-center rounded-full border transition-all ${
                          isActive
                            ? "border-robot-orange bg-white shadow-[0_0_0_4px_var(--robot-orange-soft)]"
                            : isDone
                              ? "border-robot-orange bg-robot-orange text-white"
                              : "border-robot-hairline bg-white text-robot-muted"
                        }`}
                      >
                        {isDone ? (
                          <svg width="14" height="14" viewBox="0 0 12 12" fill="none">
                            <path
                              d="M2.5 6.2L4.8 8.5L9.5 3.5"
                              stroke="currentColor"
                              strokeWidth="1.8"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                          </svg>
                        ) : (
                          <span
                            className={`text-[12px] font-semibold ${
                              isActive ? "text-robot-orange" : ""
                            }`}
                          >
                            {i + 1}
                          </span>
                        )}
                      </span>
                      <span
                        className={`absolute top-[42px] whitespace-nowrap text-[12px] font-medium tracking-[0.08em] transition-colors ${
                          isActive
                            ? "text-robot-ink"
                            : "text-robot-muted group-hover:text-robot-ink"
                        }`}
                      >
                        {step.label}
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ol>
          </div>
        </nav>
      )}


      {/* Status */}
      <div className="flex shrink-0 items-center gap-2">
        <StatusPill label="信号" value="良好" />
        <StatusPill label="电量" value="82%" />
      </div>
    </header>
  );
}

function StatusPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-2 rounded-full border border-robot-hairline bg-white/80 px-3 py-1.5 backdrop-blur-sm">
      <span className="text-[10px] font-medium tracking-[0.14em] text-robot-muted">
        {label}
      </span>
      <span className="text-[12px] font-semibold text-robot-ink">{value}</span>
    </div>
  );
}
