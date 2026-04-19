---
title: Design System
status: active
created: 2026-04-03
last_reviewed_on: 2026-04-19
review_in: 6 months
applies_to: MCP_Catalog
---

# Design System

Visual design reference for the NEPHILIM UI. Covers typography, color, CSS variables, card effects, glassmorphism, and accessibility rules.

---

## Typography

Four font families with distinct roles. All loaded via Google Fonts.

| Font | Use Case | CSS Variable / Class |
|------|----------|----------------------|
| **Orbitron** | NEPHILIM display headings, HUD-style elements | `font-orbitron` |
| **Outfit** | UI display text, section titles | `font-outfit` |
| **Manrope** | Body copy, descriptions, labels | `font-manrope` |
| **Space Mono** | Code, data values, system-style readouts | `font-mono` |

**Rules:**
- Use Orbitron sparingly — headline only, never body text
- Outfit for card titles, page headers
- Manrope for everything readable at length (descriptions, chat messages)
- Space Mono for stats, IDs, technical values

---

## Celestial Order Colors

```css
/* Celestial Order tier colors */
--wanderer-color: #C0C0C0;   /* Silver */
--sage-color:     #00BFFF;   /* Deep Sky Blue / Cyan */
--warden-color:   #DA70D6;   /* Orchid / Purple */
--archon-color:   #FFD700;   /* Gold */
```

**Tailwind equivalents:**
- Wanderer: `text-[#C0C0C0]`, `border-[#C0C0C0]/40`
- Sage: `text-[#00BFFF]`, `border-[#00BFFF]/40`
- Warden: `text-[#DA70D6]`, `border-[#DA70D6]/40`
- Archon: `text-[#FFD700]`, `border-[#FFD700]/40`

---

## CSS Variables (`index.css`)

### NEPHILIM Core Palette

```css
:root {
  --nephilim-void:    #0B0B0D;   /* Page background */
  --nephilim-cyan:    #00ffff;   /* Accent highlight */
  --nephilim-magenta: #ff00ff;   /* Secondary accent */
}
```

### Per-Persona Primary Colors

```css
:root {
  --eeva-primary:   #e0c3fc;   /* Soft violet */
  --aegis-primary:  #4a90d9;   /* Steel blue */
  --solace-primary: #7eb8da;   /* Muted sky blue */
  --nyx-primary:    #9b59b6;   /* Deep purple */
  --cipher-primary: #2ecc71;   /* Emerald green */
  --aurora-primary: #f39c12;   /* Amber/orange */
}
```

These are used for persona-specific accent theming in chat interfaces, affinity meters, and badges.

---

## Card Effects by Tier

Each Celestial Order tier has a signature animation applied to persona cards. Keyframes are defined in `react-ui/src/index.css`.

| Tier | Effect | Keyframe Name | Description |
|------|--------|---------------|-------------|
| `archon` | Solar Crown | `solar-crown-pulse` | Gold radial glow pulsing outward, subtle shimmer |
| `warden` | Void Rift | `void-rift-shimmer` | Purple energy wave sweeping across card |
| `warden` | Azure Stream | `azure-stream-flow` | Cyan light flowing from corner (Solace/Aurora variant) |
| `sage` | Dim Echo | `dim-echo-fade` | Cyan glimmer fading in/out |
| `wanderer` | Dim Echo | `dim-echo-fade` | Silver static shimmer, minimal |

**Usage pattern:**
```tsx
<div className={`card-effect-${persona.celestial_order}`}>
  {/* Card content */}
</div>
```

---

## Glassmorphism

Standard recipe used across all floating panels, cards, and overlays:

```tsx
className="bg-white/[0.05] backdrop-blur-xl border border-white/[0.1] rounded-xl"
```

**Components:**
- `bg-white/[0.05]` — 5% white fill, creates translucent glass surface
- `backdrop-blur-xl` — Blurs content behind the element (GPU-accelerated)
- `border border-white/[0.1]` — 10% white border for edge definition
- `rounded-xl` — Standard corner radius

**Variants:**
```tsx
// Elevated (more prominent panels)
"bg-white/[0.08] backdrop-blur-2xl border border-white/[0.15]"

// Subtle (background decorative panels)
"bg-white/[0.03] backdrop-blur-sm border border-white/[0.05]"
```

---

## WCAG AA Accessibility Rules

All text must meet WCAG AA contrast ratio (4.5:1 for normal text, 3:1 for large text).

**Minimum opacity rules:**

| Element | Minimum Class | Never Use |
|---------|---------------|-----------|
| Body text | `text-white/60` | `text-white/40` or lower |
| Secondary text | `text-white/70` | — |
| Disabled/hint text | `text-white/50` | `text-white/30` or lower |
| Headings | `text-white` or `text-white/90` | — |

**Key rule:** `text-white/60` is the floor. Never go below `/60` for any readable text.

**Tested against:** `#0B0B0D` (void background) and semi-transparent card surfaces.

---

## Motion & Animation

All non-trivial animations use Framer Motion for hardware acceleration and React state management.

**`prefers-reduced-motion` compliance:**
```tsx
import { useReducedMotion } from 'framer-motion'

const shouldReduceMotion = useReducedMotion()

<motion.div
  animate={shouldReduceMotion ? {} : { opacity: [0.5, 1, 0.5] }}
  transition={{ duration: 2, repeat: Infinity }}
/>
```

**General animation principles:**
- Cards: scale + opacity on hover (scale to 1.02, not more)
- Page transitions: fade + translate-y (12px max)
- Loading states: pulsing opacity cycles
- Modal/overlay: scale from 0.95 + opacity

---

## Background: `NephilimBackground`

The `NephilimBackground` component renders animated particles, aurora gradients, and void depth. Used on all pages.

```tsx
import NephilimBackground from '../components/NephilimBackground'

// In any page component
<div className="relative min-h-screen">
  <NephilimBackground />
  <div className="relative z-10">
    {/* Page content */}
  </div>
</div>
```

The background renders at `z-0`; all content must be `z-10` or higher.

---

## References

- `react-ui/src/index.css` — All CSS variables and keyframe animations
- `tailwind.config.js` — Tailwind theme extensions
- `react-ui/src/components/NephilimBackground.tsx` — Animated background
- `docs/architecture/CELESTIAL_ORDER.md` — Tier color system
