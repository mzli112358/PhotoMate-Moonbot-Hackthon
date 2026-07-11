import { useVoice } from "./voice-context";

const BAR_COUNT = 14;

export function VoiceIndicator() {
  const { state } = useVoice();

  const label =
    state === "idle"
      ? "待命"
      : state === "listening"
        ? "正在倾听"
        : state === "processing"
          ? "正在思考"
          : "正在回应";

  return (
    <div className="voice-indicator pointer-events-none fixed bottom-0 z-50 flex flex-col items-center pb-8">
      {/* Transcript — above the orb */}
      {/* Orb */}
      <div className="relative flex h-[96px] w-[96px] items-center justify-center">
        {/* Outer ripple (responding) */}
        {state === "responding" && (
          <>
            <span
              className="absolute inset-0 rounded-full border border-robot-orange/50"
              style={{ animation: "robot-pulse-ring 1.6s ease-out infinite" }}
            />
            <span
              className="absolute inset-0 rounded-full border border-robot-orange/40"
              style={{ animation: "robot-pulse-ring 1.6s ease-out 0.6s infinite" }}
            />
          </>
        )}

        {/* Idle breathing ring */}
        {state === "idle" && (
          <span
            className="absolute inset-2 rounded-full border border-robot-hairline"
            style={{ animation: "robot-breath 3.2s ease-in-out infinite" }}
          />
        )}

        {/* Processing spinner */}
        {state === "processing" && (
          <svg
            className="absolute inset-0 h-full w-full"
            style={{ animation: "robot-spin 1.2s linear infinite" }}
            viewBox="0 0 100 100"
          >
            <circle
              cx="50"
              cy="50"
              r="46"
              fill="none"
              stroke="var(--robot-orange)"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeDasharray="60 240"
            />
          </svg>
        )}

        {/* Base disc */}
        <div
          className={`relative flex h-[68px] w-[68px] items-center justify-center rounded-full transition-all duration-500 ${
            state === "listening"
              ? "bg-white shadow-[0_0_0_1px_var(--robot-orange),0_20px_60px_-20px_var(--robot-orange-glow)]"
              : state === "responding"
                ? "bg-gradient-to-br from-[var(--robot-orange)] to-[var(--robot-orange-glow)] shadow-[0_20px_60px_-15px_var(--robot-orange-glow)]"
                : state === "processing"
                  ? "bg-white shadow-[0_0_0_1px_var(--robot-hairline)]"
                  : "bg-white shadow-[0_0_0_1px_var(--robot-hairline)]"
          }`}
        >
          {/* Waveform bars for listening */}
          {state === "listening" && (
            <div className="flex h-6 items-center gap-[3px]">
              {Array.from({ length: BAR_COUNT }).map((_, i) => {
                const h = 30 + Math.sin(i * 0.9) * 20 + (i % 3) * 6;
                return (
                  <span
                    key={i}
                    className="w-[2px] rounded-full bg-robot-orange"
                    style={{
                      height: `${h}%`,
                      animation: `robot-wave ${0.7 + (i % 4) * 0.15}s ease-in-out ${i * 0.05}s infinite`,
                    }}
                  />
                );
              })}
            </div>
          )}
          {state === "responding" && (
            <div className="h-2.5 w-2.5 rounded-full bg-white/90" />
          )}
          {state === "processing" && (
            <div className="h-2 w-2 rounded-full bg-robot-orange" />
          )}
          {state === "idle" && (
            <div className="h-1.5 w-1.5 rounded-full bg-robot-muted/60" />
          )}
        </div>
      </div>

      {/* State label */}
      <div className="mt-3 flex items-center gap-2 text-[11px] font-medium tracking-[0.18em] text-robot-muted">
        <span
          className={`h-1.5 w-1.5 rounded-full ${
            state === "idle" ? "bg-robot-muted/50" : "bg-robot-orange"
          }`}
        />
        {label}
      </div>
    </div>
  );
}
