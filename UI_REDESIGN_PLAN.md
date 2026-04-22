# UI Redesign Plan

## Goals
- Deliver a premium, modern, dark-first app shell.
- Fix sidebar space usage and navigation quality.
- Unify settings readability and layout discipline.
- Add subtle motion for navigation and page transitions.

## Inspiration Summary (Research)
- Apple HIG dark mode: layered dark surfaces, adaptive contrast, avoid pure white text overload.
- Microsoft Fluent motion guidance: connected motion, context-preserving transitions, subtle timing.
- Qt official docs: use QPropertyAnimation + QGraphicsOpacityEffect for smooth low-overhead transitions and centralized stylesheet control.

## New Design System Direction
- Dark layered surfaces (`base`, `surface_0`, `surface_1`, `surface_2`).
- Accent language shifted to controlled purple?pink gradient for primary emphasis.
- Semantic text hierarchy (`text`, `text_soft`, muted role labels).
- Professional SVG icon set for nav.

## Animation Strategy
- Animated nav indicator movement on page changes.
- Fade-in on stacked page switch for continuity.
- Preserve short duration (`~180ms`) and cubic easing for responsive feel.

## Safety Strategy
- UI-only refactor; transfer/business logic preserved.
- Parser/output logic kept isolated to avoid brittle coupling.
- Compile checks run after UI changes.
