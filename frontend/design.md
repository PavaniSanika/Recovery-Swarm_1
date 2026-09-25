# DESIGN.md — RECOVERY-SWARM visual design system

Follow this exactly on every screen. Do not deviate or "improve" it per-screen.

## Tone
Clinical, calm, trustworthy. This is a decision-support tool a clinician might actually
use, not a marketing site. No gradients, no bouncy/playful animation, no emoji as UI icons
(use lucide-react icons instead), no centered hero sections.

## Layout
- Fixed left sidebar (240px) for navigation; content area fills the rest.
- Consistent page padding: 24px on desktop, 16px on mobile.
- Max content width 1280px, centered, on wide screens.
- 8px spacing scale throughout (8/16/24/32/48) — no arbitrary margins.

## Color system (define as CSS variables / Tailwind theme, use nowhere else)
- Background: near-white (#F8FAFC), cards: white with a 1px border (#E2E8F0), not heavy shadows.
- Text: near-black (#0F172A) for primary, slate gray (#64748B) for secondary.
- One accent color for interactive elements (links, active nav, primary buttons) — pick a
  single deliberate blue or teal, not a gradient.
- Status colors used ONLY for their meaning, never decoratively:
  green = on_track/allow, yellow = slightly_below/caution, orange = below_expected/modify,
  red = deteriorating/escalate. Same four colors everywhere (trajectory, safety badges,
  screening severity, 3D body outline).

## Typography
- One font family (system UI stack or a single Google Font, loaded once).
- Clear scale: page title 24px semibold, section heading 16px semibold, body 14px, label/
  caption 12px uppercase tracked (for things like "RECOVERY SCORE").
- Numbers that matter (scores, targets) get visual weight: larger size, semibold, not just
  plain text inline with a sentence.

## Components (reuse the same ones everywhere, don't rebuild per screen)
- Card: white, 1px border, 8px radius, 16-24px padding. This is the base unit for almost
  everything (stat cards, agent cards, plan items).
- Badge/pill: small, rounded-full, colored background + colored text (using the status
  colors above) — for safety results, trajectory, agent status, screening severity.
- Button: solid accent for primary actions (Optimize Recovery, Run What-If), outline/ghost
  for secondary (Reset, Advance 1 Hour). Consistent height (36-40px), consistent radius.
- Empty/loading/error states: every screen and every data-fetching component must handle
  all three, using the same skeleton/spinner/error-banner pattern, not ad hoc per screen.

## Charts (Recharts)
- Consistent axis styling, consistent line colors per metric across all charts (e.g. pain
  is always the same color wherever it appears).
- Label axes and include units. No default Recharts styling left unstyled.

## Motion
- Subtle only: 150-200ms ease transitions on hover/state change. No page-transition
  animations, no confetti, no bounce easing.

## Demo Mode bar
- Visually distinct from the six main screens (e.g. a slightly different background tint
  or a top strip) so it reads as "control panel," not part of the clinical UI itself —
  judges should be able to tell at a glance which parts are "the product" vs "our demo
  remote control."

## What "industry ready" excludes
No lorem ipsum, no placeholder images, no console.log left in, no unstyled default HTML
elements (native <select>, native <button> without a class) anywhere in the six main screens.