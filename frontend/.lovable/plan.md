# Robot Photo Assistant — 15" Landscape UI

A voice-first interface for a consumer robot that approaches users and takes photos. Six sequential screens, each optimized for a 1920×1200-ish landscape display, with a persistent voice indicator anchoring every screen.

## Design language

- **Palette**: white background (#FAFAFA / pure white surfaces), deep black (#0A0A0A) for text and structure, signal orange (#FF5A1F) reserved for active state, voice reactivity, and the selected option only. Neutral warm grays for borders (~4% black) and secondary text.
- **Typography**: geometric sans for display (Space Grotesk or similar), neutral grotesk for body (Inter Tight). Large, confident hierarchy — a robot screen is read from 1–2m away.
- **Surface**: predominantly white, soft 20–24px radius cards, hairline 1px borders at very low contrast, subtle ambient shadow. No heavy chrome, no gradients on cards. One orange gradient reserved for the voice indicator's active halo.
- **Motion**: calm, purposeful. Voice orb pulses with amplitude. Selected cards animate in with a soft orange border draw + subtle scale. Screen transitions cross-fade with a shared voice indicator that never remounts.
- **No touch affordances**: option cards read as *previews*, not buttons. No "Tap to continue," no visible tap targets, no hover cursors. Small "Say [command]" hints appear under each card in muted gray.

## Persistent element: Voice indicator (bottom center)

Always visible, fixed ~48px from bottom, centered. A circular orb roughly 96–120px with:

- **Idle**: soft gray ring, slow breathing pulse.
- **Listening**: orange ring, live waveform bars radiating from center, reacting to (future) mic amplitude.
- **Processing**: rotating orange arc segments, no waveform.
- **Responding**: orange fill with concentric ripple, spoken transcript rendered as a single line of light gray text just above the orb.

Directly above the orb: a slim transcript line ("You said: …") and current suggested voice commands as ghost chips (e.g. `"Say 'take photo'"`, `"Say 'use my phone'"`).

## Screen 1 — Approaching User

Full-bleed minimal map/scene view.

- **Left 60%**: top-down stylized floor plan with the robot's path drawn as a dotted orange line from origin to a pulsing orange target dot. Muted gray floor, black obstacles, a subtle grid.
- **Right 40%**: status card stack — status label "On the way" in large type, ETA ("~6 seconds"), distance ("3.2 m"), and a small user avatar/label ("Approaching guest").
- Top bar: minimal — small robot ID chip left, connectivity/battery pill right. No back button.

## Screen 2 — Arrival Prompt

Centered composition.

- Oversized display headline: "Want a photo?"
- Sub: "Say yes to start, or no to dismiss."
- Two large preview cards side-by-side below: **Yes, let's shoot** and **Not now**. Cards are visual previews only — Yes card shows a subtle camera glyph, No card is neutral. Voice hint under each.
- Voice orb below, in listening state.

## Screen 3 — Capture Device Selection

Two-card layout, equal weight, centered horizontally.

- **Card A — Your phone**: iconographic phone illustration, label "Your smartphone," sub "We'll send the shot to your device." Voice hint: `Say "my phone"`.
- **Card B — Robot camera**: Insta360 render, label "Insta360 on robot," sub "360° capture, instant preview." Voice hint: `Say "robot camera"`.
- Selected card (post voice recognition) gets orange border stroke, soft orange tint background, and a small "Selected" pill. Unselected dims to 60% opacity.

## Screen 4 — Capture Mode Selection

Two-tier layout.

- **Top row**: two primary mode cards — **One-tap photo** and **Video recording** — same visual treatment as Screen 3.
- **Bottom row (revealed when Video is selected via voice)**: horizontal scroll of cinematic preset cards — Orbit, Dolly-in, Reveal, Crane-up, Follow, Static. Each preset card shows a small motion diagram (arrow path over a subject silhouette), name, and duration. Voice hint under each: `Say "orbit"`, etc.
- Selected preset gets the same orange highlight treatment.

## Screen 5 — Live Preview (Insta360 only)

Immersive.

- **Main area**: full-bleed live camera feed with a subtle white inner border framing it as a viewport, not a chrome-heavy overlay.
- **Top-left overlay chip**: current mode ("Video · Orbit").
- **Top-right overlay chip**: recording status — red dot + timecode ("● 00:04") when recording, or "Ready" in white when idle.
- **Bottom-left**: small voice command hints (`"stop"`, `"restart"`, `"switch to photo"`).
- Voice orb still bottom-center, floating over feed with a soft backdrop-blur pill behind it for legibility.

## Screen 6 — Post-Capture

Split 50/50 with a thin vertical divider.

- **Left half**: large QR code on a white card, label "Scan to transfer," sub "Photos + video, expires in 10 min." Small filename/thumbnail strip below QR.
- **Right half**: printer prompt — Xiaomi printer product render, headline "Print it?", sub "4×6 instant print via Xiaomi printer." Two preview cards below: **Print one** and **Skip**. Voice hints under each.
- After voice selection, right side transitions to a printing progress state (paper-feed animation) while the left QR stays available.

## Technical notes

- New route per screen under `src/routes/`: `index.tsx` (Approaching), `arrival.tsx`, `device.tsx`, `mode.tsx`, `preview.tsx`, `post.tsx`. Real routes, not hash anchors — each gets its own `head()` metadata.
- Shared `<VoiceIndicator />` component in `src/components/voice-indicator.tsx`, rendered inside a layout route so it persists across navigations without remount. Accepts a `state` prop (`idle | listening | processing | responding`) and an optional `transcript` string. Waveform stubbed with CSS-animated bars now, wired to a `useVoiceAmplitude()` hook returning 0 for future mic integration.
- Shared `<OptionCard />` component with `selected` prop that triggers the orange highlight animation via Framer Motion.
- Design tokens added to `src/styles.css` under `:root`: `--robot-orange: oklch(0.68 0.19 40)`, `--robot-orange-soft`, `--robot-ink`, `--robot-hairline`. Mapped in `@theme inline` as `--color-robot-orange` etc.
- Fonts: Space Grotesk + Inter Tight loaded via `<link>` in `__root.tsx` head, registered as `--font-display` / `--font-body` in `@theme`.
- `head()` in `__root.tsx` updated with real app-specific title/description (replacing "Lovable App" defaults).
- Preview viewport set to landscape tablet/desktop dimensions matching a 15" display.
- Framer Motion used for card selection animation, screen transitions, and voice orb pulse. No touch/hover-only interactions; all state changes are driven by simulated voice events (dev-only keyboard shortcuts 1/2/3 to simulate voice recognition selecting an option, for demoability).

## Out of scope

- Real microphone capture, real speech-to-text, real camera feed, real printer integration, real navigation/SLAM. All screens are UI shells with simulated state.
- No backend/Cloud enabled — this is a presentation UI only.
