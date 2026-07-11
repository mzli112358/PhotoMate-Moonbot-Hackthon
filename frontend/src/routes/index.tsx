import { createFileRoute } from "@tanstack/react-router";
import { HackthonMap } from "../components/hackthon-map";
import { useVoiceScene } from "../components/voice-context";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [{ title: "导航 · PhotoMate 指挥台" }],
  }),
  component: PrepareScreen,
});

function PrepareScreen() {
  useVoiceScene({
    state: "listening",
    transcript: "",
    hints: ["前往点位", "停止导航"],
  });

  return (
    <main className="h-full">
      <HackthonMap />
    </main>
  );
}
