import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type VoiceState = "idle" | "listening" | "processing" | "responding";

export interface VoiceContextValue {
  state: VoiceState;
  transcript: string;
  hints: string[];
  set: (opts: { state?: VoiceState; transcript?: string; hints?: string[] }) => void;
}

const VoiceContext = createContext<VoiceContextValue | null>(null);

export function VoiceProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<VoiceState>("listening");
  const [transcript, setTranscript] = useState<string>("");
  const [hints, setHints] = useState<string[]>([]);

  const set: VoiceContextValue["set"] = (opts) => {
    if (opts.state !== undefined) setState(opts.state);
    if (opts.transcript !== undefined) setTranscript(opts.transcript);
    if (opts.hints !== undefined) setHints(opts.hints);
  };

  return (
    <VoiceContext.Provider value={{ state, transcript, hints, set }}>
      {children}
    </VoiceContext.Provider>
  );
}

export function useVoice() {
  const ctx = useContext(VoiceContext);
  if (!ctx) throw new Error("useVoice must be used within VoiceProvider");
  return ctx;
}

/** Convenience hook: sets scene-specific voice state on mount. */
export function useVoiceScene(opts: { state: VoiceState; transcript?: string; hints?: string[] }) {
  const { set } = useVoice();
  useEffect(() => {
    set({ state: opts.state, transcript: opts.transcript ?? "", hints: opts.hints ?? [] });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opts.state, opts.transcript, JSON.stringify(opts.hints)]);
}
