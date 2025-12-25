# Header Component Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Header.tsx (222 lines)                            │
│                     Main Composition + State Management                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  State:                                                                     │
│  • currentTheme: 'legendary' | 'epic' | 'rare'                              │
│  • isMobileMenuOpen: boolean                                                │
│                                                                             │
│  Logic:                                                                     │
│  • Theme determination (persona rarity > page path)                         │
│  • Background animation generation                                          │
│  • Animation variants definition                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ composes
                                       │
       ┌───────────────────────────────┼───────────────────────────────┐
       │                               │                               │
       ▼                               ▼                               ▼
┌──────────────────┐          ┌──────────────────┐          ┌──────────────────┐
│ HeaderVisuals.tsx│          │HeaderNavigation  │          │  MobileMenu.tsx  │
│    (86 lines)    │          │  .tsx (240 lines)│          │   (190 lines)    │
│                  │          │                  │          │                  │
│ Visual Effects   │          │ Branding + Nav   │          │   Mobile UI      │
└──────────────────┘          └──────────────────┘          └──────────────────┘
       │                               │                               │
       │ exports                       │ exports                       │ exports
       │                               │                               │
       ▼                               ▼                               ▼
┌──────────────────┐          ┌──────────────────┐          ┌──────────────────┐
│FloatingParticles │          │ HeaderBranding   │          │   MobileMenu     │
│                  │          │                  │          │                  │
│ • 12 particles   │          │ • Logo + glow    │          │ • Slide-in panel │
│ • Random motion  │          │ • Brand text     │          │ • Backdrop blur  │
│ • Continuous     │          │ • Gradient anim  │          │ • Persona info   │
│   animation      │          │                  │          │ • Session info   │
└──────────────────┘          └──────────────────┘          │ • Nav links      │
                                                            │ • Theme indicator│
┌──────────────────┐          ┌──────────────────┐          └──────────────────┘
│HeaderBackground  │          │DesktopNavigation │
│                  │          │                  │
│ • 3-layer glass  │          │ • 3 nav links    │
│ • Theme gradient │          │ • Active colors  │
│ • Animated border│          │ • Hover effects  │
│                  │          │ • Particle FX    │
└──────────────────┘          └──────────────────┘
```

---

## Component Hierarchy (JSX Tree)

```jsx
<motion.header className="relative overflow-hidden">
  {/* ============== HeaderVisuals.tsx ============== */}
  <HeaderBackground
    currentTheme={currentTheme}
    getBackgroundAnimation={getBackgroundAnimation}
  >
    <div className="glassmorphism-layer-1" />
    <div className="glassmorphism-layer-2" />
    <div className="glassmorphism-layer-3" />
    <motion.div className="theme-gradient-animation" />
    <FloatingParticles />
    <motion.div className="animated-border" />
  </HeaderBackground>

  <div className="max-w-7xl mx-auto">
    <motion.div className="flex justify-between items-center">

      {/* ============== HeaderNavigation.tsx ============== */}
      <HeaderBranding itemVariants={itemVariants}>
        <motion.div className="logo-container">
          <motion.div className="animated-logo">
            🎭
          </motion.div>
        </motion.div>
        <div className="brand-text">
          <motion.h1>Persona Chat</motion.h1>
          <motion.p>Gacha Style</motion.p>
        </div>
      </HeaderBranding>

      {/* ============== HeaderNavigation.tsx ============== */}
      <DesktopNavigation
        itemVariants={itemVariants}
        navItemVariants={navItemVariants}
      >
        <motion.nav>
          <Link to="/">Home</Link>
          <Link to="/select">Characters</Link>
          <Link to="/chat">Chat</Link>
        </motion.nav>
      </DesktopNavigation>

      {/* ============== Header.tsx ============== */}
      <motion.div className="controls">
        <motion.button onClick={toggleMute}>
          {/* Audio Control SVG */}
        </motion.button>

        <motion.button onClick={() => setIsMobileMenuOpen(true)}>
          {/* Mobile Menu Button SVG */}
        </motion.button>
      </motion.div>

    </motion.div>
  </div>

  {/* ============== MobileMenu.tsx ============== */}
  <MobileMenu
    isMobileMenuOpen={isMobileMenuOpen}
    setIsMobileMenuOpen={setIsMobileMenuOpen}
    selectedPersona={selectedPersona}
    currentSession={currentSession}
    currentTheme={currentTheme}
  >
    <AnimatePresence>
      {isMobileMenuOpen && (
        <>
          <motion.div className="backdrop" />
          <motion.div className="menu-panel">
            <div className="menu-header">
              <h2>Menu</h2>
              <button onClick={closeMobileMenu}>×</button>
            </div>
            <div className="menu-content">
              <div className="persona-display" />
              <div className="session-display" />
              <nav className="mobile-nav">
                <Link to="/">🏠 Home</Link>
                <Link to="/select">🎭 Characters</Link>
                <Link to="/chat">💬 Chat</Link>
              </nav>
              <div className="theme-indicator" />
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  </MobileMenu>

</motion.header>
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Parent Components                        │
│                  (PersonaContext, AudioContext)                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ provides
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                          Header.tsx                             │
│                                                                 │
│  Receives:                                                      │
│  • selectedPersona (from PersonaContext)                        │
│  • currentSession (from PersonaContext)                         │
│  • location (from useLocation)                                  │
│  • isMuted, toggleMute (from AudioContext)                      │
│                                                                 │
│  Computes:                                                      │
│  • currentTheme (based on persona/page)                         │
│  • getBackgroundAnimation (theme-based gradients)               │
│  • Animation variants                                           │
│                                                                 │
│  Manages:                                                       │
│  • isMobileMenuOpen state                                       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ passes props
                                │
       ┌────────────────────────┼────────────────────────┐
       │                        │                        │
       ▼                        ▼                        ▼
┌─────────────┐        ┌─────────────┐        ┌─────────────┐
│HeaderVisuals│        │HeaderNav    │        │ MobileMenu  │
│             │        │             │        │             │
│ Props:      │        │ Props:      │        │ Props:      │
│ • theme     │        │ • variants  │        │ • isOpen    │
│ • getAnim   │        │             │        │ • setIsOpen │
│             │        │ Uses:       │        │ • persona   │
│ Renders:    │        │ • location  │        │ • session   │
│ • Particles │        │   (hook)    │        │ • theme     │
│ • Gradient  │        │             │        │             │
│ • Border    │        │ Renders:    │        │ Renders:    │
│             │        │ • Logo      │        │ • Panel     │
│             │        │ • Nav links │        │ • Nav       │
└─────────────┘        └─────────────┘        └─────────────┘
```

---

## Theme Propagation Flow

```
User Action / Route Change
         │
         ▼
    useEffect in Header.tsx
         │
         ├─ Check selectedPersona
         │       │
         │       ├─ legendary → 'legendary'
         │       ├─ epic      → 'epic'
         │       └─ rare      → 'rare'
         │
         ├─ Fallback to location.pathname
         │       │
         │       ├─ /        → 'legendary'
         │       ├─ /select  → 'epic'
         │       └─ /chat    → 'rare'
         │
         ▼
    setCurrentTheme(newTheme)
         │
         ├─ Triggers re-render
         │
         ▼
    Propagates to:
         │
         ├─ HeaderBackground (theme-based gradients)
         │       │
         │       └─ getBackgroundAnimation() returns new colors
         │
         ├─ HeaderNavigation (active link colors)
         │       │
         │       └─ getActiveColor() returns themed colors
         │
         └─ MobileMenu (theme indicator)
                 │
                 └─ Theme dot color updates
```

---

## Animation Orchestration

```
Container Variants (Header.tsx)
    │
    ├─ containerVariants
    │   └─ Stagger children by 0.1s
    │
    ├─ itemVariants
    │   └─ Fade in + slide down
    │
    └─ navItemVariants
        └─ Scale on hover/tap

        ▼ passed to ▼

HeaderBranding
    │
    └─ Logo animations
        ├─ Box shadow pulse (3s loop)
        ├─ Emoji rotation (2s loop)
        └─ Background glow scale (2s loop)

DesktopNavigation
    │
    └─ Nav link animations
        ├─ Text shadow pulse (2s loop, if active)
        ├─ Background glow on hover
        └─ Particle effects on hover (3 particles)

HeaderBackground
    │
    └─ Visual effects
        ├─ FloatingParticles (12 × 4-7s loops)
        ├─ Theme gradient (6s loop)
        └─ Border colors (8s loop)

MobileMenu
    │
    └─ Panel animations
        ├─ Slide-in (spring physics)
        ├─ Backdrop fade (opacity 0→1)
        └─ Content stagger (0.1s delays)
```

---

## Props Interface Summary

### HeaderBackground
```typescript
interface HeaderBackgroundProps {
  currentTheme: 'legendary' | 'epic' | 'rare';
  getBackgroundAnimation: () => {
    background: string[];
  };
}
```

### HeaderBranding
```typescript
interface HeaderBrandingProps {
  itemVariants: {
    hidden: { opacity: 0; y: -10 };
    visible: { opacity: 1; y: 0; transition: { duration: 0.4 } };
  };
}
```

### DesktopNavigation
```typescript
interface DesktopNavigationProps {
  itemVariants: Variants;
  navItemVariants: {
    idle: { scale: 1 };
    hover: { scale: 1.05 };
    tap: { scale: 0.95 };
  };
}
```

### MobileMenu
```typescript
interface MobileMenuProps {
  isMobileMenuOpen: boolean;
  setIsMobileMenuOpen: (open: boolean) => void;
  selectedPersona: {
    display_name: string;
    rarity: string;
  } | null;
  currentSession: {
    title: string;
    message_count: number;
  } | null;
  currentTheme: 'legendary' | 'epic' | 'rare';
}
```

---

## File Size Comparison

```
Before Refactoring:
┌────────────────────────────┐
│      Header.tsx            │
│       646 lines            │
│                            │
│  • Visual effects          │
│  • Branding                │
│  • Desktop navigation      │
│  • Mobile menu             │
│  • State management        │
│  • Theme logic             │
│  • Animation variants      │
└────────────────────────────┘

After Refactoring:
┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│HeaderVisuals  │  │HeaderNav      │  │ MobileMenu    │  │ Header.tsx    │
│  86 lines     │  │ 240 lines     │  │ 190 lines     │  │ 222 lines     │
│               │  │               │  │               │  │               │
│ • Particles   │  │ • Branding    │  │ • Panel       │  │ • State       │
│ • Background  │  │ • Desktop nav │  │ • Backdrop    │  │ • Theme logic │
│ • Border      │  │ • Link effects│  │ • Nav links   │  │ • Composition │
└───────────────┘  └───────────────┘  └───────────────┘  └───────────────┘
     13.3%              32.4%              25.6%              29.9%
```

---

## Import Graph

```
Header.tsx
    │
    ├─ import React, { useEffect, useState } from 'react'
    ├─ import { useLocation } from 'react-router-dom'
    ├─ import { motion, Variants } from 'framer-motion'
    ├─ import { usePersona } from '../context/PersonaContext'
    ├─ import { useAudio } from '../context/AudioContext'
    ├─ import { HeaderBackground } from './header/HeaderVisuals'
    ├─ import { HeaderBranding, DesktopNavigation } from './header/HeaderNavigation'
    └─ import { MobileMenu } from './header/MobileMenu'

HeaderVisuals.tsx
    │
    ├─ import React from 'react'
    └─ import { motion } from 'framer-motion'

HeaderNavigation.tsx
    │
    ├─ import React from 'react'
    ├─ import { Link, useLocation } from 'react-router-dom'
    └─ import { motion, AnimatePresence, Variants } from 'framer-motion'

MobileMenu.tsx
    │
    ├─ import React, { useEffect } from 'react'
    ├─ import { Link } from 'react-router-dom'
    └─ import { motion, AnimatePresence, Variants } from 'framer-motion'
```

---

## Reusability Matrix

| Component | Reusable | Portable | Dependencies |
|-----------|----------|----------|--------------|
| FloatingParticles | ✅ Yes | ✅ Yes | None |
| HeaderBackground | ✅ Yes | ✅ Yes | Theme prop |
| HeaderBranding | ⚠️ Partial | ⚠️ Partial | Variants prop |
| DesktopNavigation | ⚠️ Partial | ⚠️ Partial | Location, Variants |
| MobileMenu | ⚠️ Partial | ⚠️ Partial | Persona/Session data |
| Header | ❌ No | ❌ No | Multiple contexts |

**Legend:**
- ✅ Yes: Can be used as-is in other components
- ⚠️ Partial: Can be adapted with minimal changes
- ❌ No: Tightly coupled to current use case

---

## Performance Characteristics

### Render Frequency

```
Header.tsx
    Re-renders on:
    • selectedPersona change
    • location.pathname change
    • isMobileMenuOpen change
    • isMuted change

    Frequency: Medium (route changes, menu toggles)

HeaderVisuals.tsx
    Re-renders on:
    • currentTheme change

    Frequency: Low (theme changes only)

    Optimization potential: React.memo ✅

HeaderNavigation.tsx
    Re-renders on:
    • location.pathname change

    Frequency: Low (route changes only)

    Optimization potential: React.memo ✅

MobileMenu.tsx
    Re-renders on:
    • isMobileMenuOpen change
    • selectedPersona change
    • currentSession change
    • currentTheme change

    Frequency: Medium (menu toggles, context updates)

    Optimization potential: React.memo with shallow compare ✅
```

### Animation Performance

```
Hardware-Accelerated Properties Used:
    ✅ transform (translate, scale, rotate)
    ✅ opacity
    ❌ background (not hardware-accelerated, but acceptable for gradient animations)

60 FPS Maintained:
    ✅ FloatingParticles (12 particles, staggered)
    ✅ Logo animations (rotate, scale)
    ✅ Border color cycle
    ✅ Mobile menu slide-in
    ⚠️ Background gradient (may drop to 30 FPS on low-end devices)
```

---

## Accessibility Features

```
Keyboard Navigation:
    ✅ All links focusable
    ✅ Escape key closes mobile menu
    ⚠️ Focus trap in mobile menu (TODO)
    ⚠️ Skip to content link (TODO)

ARIA Labels:
    ✅ Audio button: "Mute audio" / "Unmute audio"
    ✅ Mobile menu button: "Open mobile menu"
    ✅ Close button: "Close mobile menu"
    ⚠️ Navigation landmarks (TODO)

Color Contrast:
    ✅ Text on dark background (WCAG AA compliant)
    ⚠️ Active link glow (may fail for colorblind users)
    ⚠️ Theme indicator dot (decorative only)

Screen Reader Support:
    ✅ Semantic HTML (nav, header, button)
    ⚠️ Live region announcements (TODO)
    ⚠️ Menu state announcements (TODO)
```

---

This diagram provides a comprehensive visual overview of the Header component architecture after modular refactoring.
