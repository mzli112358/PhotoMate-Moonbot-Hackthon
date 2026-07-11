import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useVoiceScene } from "../components/voice-context";

export const Route = createFileRoute("/phone-countdown")({
  head: () => ({ meta: [{ title: "手机拍摄倒计时 · PhotoMate" }] }),
  component: PhoneCountdownScreen,
});

function PhoneCountdownScreen() {
  const navigate = useNavigate();
  const [count, setCount] = useState(3);

  useVoiceScene({
    state: "processing",
    transcript: "",
    hints: [],
  });

  useEffect(() => {
    if (count <= 0) {
      const doneTimer = window.setTimeout(() => {
        navigate({ to: "/phone-finish" });
      }, 700);
      return () => window.clearTimeout(doneTimer);
    }

    const timer = window.setTimeout(() => {
      setCount((value) => value - 1);
    }, 1000);

    return () => window.clearTimeout(timer);
  }, [count, navigate]);

  return (
    <main className="flex min-h-screen items-center justify-center px-8 pb-28 pt-24">
      <section className="flex w-full max-w-[980px] flex-col items-center text-center">
        <div className="text-[11px] font-semibold tracking-[0.24em] text-robot-orange">
          手机拍摄
        </div>
        <h1 className="mt-5 font-display text-[56px] font-medium leading-none text-robot-ink">
          保持微笑
        </h1>
        <p className="mt-5 max-w-[520px] text-[16px] leading-relaxed text-robot-muted">
          手机已经准备拍摄。请看向镜头，PhotoMate 将在倒计时结束后完成拍摄。
        </p>

        <div className="mt-14 flex aspect-square w-[min(52vw,360px)] items-center justify-center rounded-full border border-robot-hairline bg-card shadow-[0_28px_90px_-54px_rgba(20,15,10,0.55)]">
          <div className="font-display text-[clamp(96px,18vw,180px)] font-medium leading-none text-robot-orange">
            {count > 0 ? count : "✓"}
          </div>
        </div>

        <div className="mt-12 grid w-full max-w-[620px] grid-cols-3 gap-3">
          {[3, 2, 1].map((step) => (
            <div
              key={step}
              className={`h-2 rounded-full transition ${
                count <= step - 1 ? "bg-robot-orange" : "bg-robot-hairline"
              }`}
            />
          ))}
        </div>
      </section>
    </main>
  );
}
