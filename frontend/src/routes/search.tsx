import { createFileRoute } from "@tanstack/react-router";
import { PreviewScreen } from "./preview";

export const Route = createFileRoute("/search")({
  head: () => ({ meta: [{ title: "寻人 · 陪伴机器人 R-07" }] }),
  component: PreviewScreen,
});
