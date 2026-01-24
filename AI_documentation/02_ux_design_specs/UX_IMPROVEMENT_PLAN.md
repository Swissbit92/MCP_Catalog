# UX Improvement Implementation Plan

**Document Version:** 1.1
**Created:** 2025-12-26
**Last Updated:** 2025-12-28
**Status:** Phase 1.1 Complete ✅ | In Progress
**Estimated Total Effort:** 12-16 hours
**Completed:** 1-2 hours (Phase 1.1 Typography System)

---

## Executive Summary

This plan addresses the findings from the comprehensive UX assessment conducted on 2025-12-26. The AI Companions application currently scores **7.2/10** in overall UX quality, with significant opportunities for improvement in visual design, accessibility, and user experience. By implementing these changes, we can achieve a **9.5/10** rating and create a truly distinctive, memorable interface.

**Key Focus Areas:**
1. Typography system overhaul
2. Signature visual identity
3. WCAG AA accessibility compliance
4. Enhanced search functionality
5. Animation performance optimization

---

## Priority Tiers

### 🔥 Critical Priority (Must Do First)
**Total Estimated Effort:** 4-6 hours
**Impact:** Immediate visual differentiation + accessibility compliance

### ⚡ High Impact (Do Next)
**Total Estimated Effort:** 6-8 hours
**Impact:** Major UX improvements for power users + performance

### 💎 Nice to Have (Later)
**Total Estimated Effort:** 8-12 hours
**Impact:** Feature completeness + polish

---

## Phase 1: Critical Improvements

### 1.1 Typography System Overhaul ✅ COMPLETE (Dec 28, 2025)

**Estimated Time:** 1-2 hours → **Actual: 1.5 hours**
**Priority:** 🔥 Critical
**Status:** ✅ **IMPLEMENTED & DEPLOYED**
**Files Modified:** `react-ui/src/index.css`, `react-ui/public/index.html`, `react-ui/tailwind.config.js`, `Home.tsx`, `CharacterCardV2.module.css`, `MessageBubble.tsx`
**Impact Score:** ⭐⭐⭐⭐⭐
**Implementation Doc:** `AI_documentation/01_implementation_history/TYPOGRAPHY_SYSTEM_IMPLEMENTATION.md`

#### Problem Statement
Current typography uses default Create React App system fonts:
```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', ...
```
This creates zero visual personality and makes the app indistinguishable from generic React dashboards.

#### Solution Design

**Chosen Aesthetic:** Futuristic Gacha / Sci-Fi AI Companion theme

**Font Stack:**
- **Display (Headings, Character Names):** Orbitron (700, 900 weights)
- **Body (UI Text, Messages):** Poppins (400, 600, 700 weights)
- **Mono (Technical Info, Stats):** Space Mono (400, 700 weights)

#### Implementation Steps

**Step 1: Import Google Fonts**

**File:** `react-ui/public/index.html`

```html
<!-- Add to <head> section BEFORE other stylesheets -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Poppins:wght@400;600;700&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
```

**Step 2: Update Base Typography**

**File:** `react-ui/src/index.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Typography System */
:root {
  /* Font families */
  --font-display: 'Orbitron', sans-serif;
  --font-body: 'Poppins', sans-serif;
  --font-mono: 'Space Mono', monospace;

  /* Type scale */
  --text-xs: 0.75rem;     /* 12px */
  --text-sm: 0.875rem;    /* 14px */
  --text-base: 1rem;      /* 16px */
  --text-lg: 1.125rem;    /* 18px */
  --text-xl: 1.25rem;     /* 20px */
  --text-2xl: 1.5rem;     /* 24px */
  --text-3xl: 1.875rem;   /* 30px */
  --text-4xl: 2.25rem;    /* 36px */
  --text-5xl: 3rem;       /* 48px */
}

body {
  margin: 0;
  font-family: var(--font-body);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  font-size: var(--text-base);
  line-height: 1.6;
}

/* Headings use display font */
h1, h2, h3, h4, h5, h6 {
  font-family: var(--font-display);
  font-weight: 700;
  letter-spacing: 0.02em;
  line-height: 1.2;
}

h1 { font-size: var(--text-4xl); font-weight: 900; }
h2 { font-size: var(--text-3xl); }
h3 { font-size: var(--text-2xl); }
h4 { font-size: var(--text-xl); }

/* Monospace for code and technical data */
code, pre, .font-mono {
  font-family: var(--font-mono);
}

/* Utility classes */
.font-display { font-family: var(--font-display); }
.font-body { font-family: var(--font-body); }
.font-mono { font-family: var(--font-mono); }
```

**Step 3: Update Tailwind Config**

**File:** `react-ui/tailwind.config.js`

```javascript
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ['Orbitron', 'sans-serif'],
        body: ['Poppins', 'sans-serif'],
        mono: ['Space Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
```

**Step 4: Update Component Typography**

**File:** `react-ui/src/pages/Home.tsx`

```tsx
// Update heading
<h1 className="text-4xl md:text-6xl font-display font-black text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 via-purple-400 to-blue-400 mb-4">
  AI Companions
</h1>
<p className="text-xl font-body text-gray-300 max-w-3xl mx-auto mb-8">
  Connect with intelligent AI companions through our gacha-style agent selection system
</p>
```

**File:** `react-ui/src/components/CharacterCardV2.module.css`

```css
.character-name {
  font-family: var(--font-display);
  font-weight: 900;
  font-size: 1.1em;
  line-height: 1.1;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  /* ... existing styles ... */
}

.character-style {
  font-family: var(--font-body);
  font-size: 0.9em;
  font-weight: 600;
  /* ... existing styles ... */
}
```

**File:** `react-ui/src/components/MessageBubble.tsx`

```tsx
{/* Latency display with monospace font */}
{message.latency && (
  <span className="text-blue-400 font-mono text-xs">
    <span className="sr-only">Response time: </span>
    {message.latency < 1000
      ? `${message.latency}ms`
      : `${(message.latency / 1000).toFixed(1)}s`
    }
  </span>
)}
```

#### Testing Checklist

- [ ] All headings render in Orbitron font
- [ ] Body text renders in Poppins font
- [ ] Latency/technical stats render in Space Mono
- [ ] Character card names are bold and uppercase
- [ ] Font weights load correctly (check Network tab)
- [ ] Mobile devices show correct fonts (test on real device)
- [ ] Fallback fonts work if Google Fonts fails to load

#### Rollback Plan

If fonts cause performance issues or fail to load:
1. Revert `index.html` changes
2. Restore original `index.css` font-family
3. Consider self-hosting fonts via `/public/fonts/`

---

### 1.2 Signature Background Aesthetic

**Estimated Time:** 1 hour
**Priority:** 🔥 Critical
**Files Modified:** `react-ui/src/index.css`, `react-ui/src/pages/Home.tsx`, `react-ui/src/pages/Chat.tsx`
**Impact Score:** ⭐⭐⭐⭐⭐

#### Problem Statement
Current backgrounds use generic slate gradients (`from-slate-900 via-slate-800 to-slate-900`) with no distinctive visual identity. The app needs a **signature aesthetic** present on every page.

#### Solution Design

**Chosen Aesthetic:** Deep Space / Cosmic theme (aligns with "AI Companions" sci-fi positioning)

**Design Principles:**
- Dark base (maintains current dark mode)
- Subtle nebula-like gradients
- Multiple depth layers for parallax feel
- Rarity accents overlay on top (don't replace)

#### Implementation Steps

**Step 1: Define Global Background System**

**File:** `react-ui/src/index.css`

```css
/* Add after typography system */

/* Background System - Deep Space Aesthetic */
:root {
  /* Core background colors */
  --bg-space-dark: #0a0e27;
  --bg-space-mid: #1a1625;
  --bg-space-light: #0f0d1f;

  /* Nebula accent colors */
  --nebula-blue: rgba(59, 130, 246, 0.12);
  --nebula-purple: rgba(139, 92, 246, 0.08);
  --nebula-cyan: rgba(34, 211, 238, 0.06);

  /* Gradient definitions */
  --bg-primary: linear-gradient(180deg, var(--bg-space-dark) 0%, var(--bg-space-mid) 50%, var(--bg-space-light) 100%);
  --bg-nebula:
    radial-gradient(ellipse at 20% 30%, var(--nebula-blue), transparent 60%),
    radial-gradient(ellipse at 80% 70%, var(--nebula-purple), transparent 60%),
    radial-gradient(ellipse at 50% 50%, var(--nebula-cyan), transparent 70%);

  /* Card/surface backgrounds */
  --bg-card: rgba(30, 41, 59, 0.6);
  --bg-glass: rgba(255, 255, 255, 0.05);
  --bg-overlay: rgba(0, 0, 0, 0.4);
}

/* Base app background */
.app-background {
  background: var(--bg-primary);
  position: relative;
}

.app-background::before {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--bg-nebula);
  opacity: 0.6;
  pointer-events: none;
  z-index: 0;
}

/* Utility classes */
.bg-space { background: var(--bg-primary); }
.bg-nebula { background: var(--bg-nebula); }
.bg-card { background: var(--bg-card); }
.bg-glass { background: var(--bg-glass); backdrop-filter: blur(12px); }
```

**Step 2: Update App.tsx**

**File:** `react-ui/src/App.tsx`

```tsx
function App() {
  return (
    <AudioProvider>
      <div className="App h-screen flex flex-col app-background">
        <Header />
        <div className="flex-1 overflow-auto relative z-10">
          <Routes>
            {/* ... routes ... */}
          </Routes>
        </div>
      </div>
    </AudioProvider>
  );
}
```

**Step 3: Update Home.tsx**

**File:** `react-ui/src/pages/Home.tsx`

```tsx
// REPLACE current background div
return (
  <div className="min-h-screen relative overflow-hidden">
    {/* Deep space background (replaces slate gradient) */}
    <div className="absolute inset-0 bg-space"></div>
    <div className="absolute inset-0 bg-nebula opacity-60"></div>

    {/* Animated stars layer */}
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {[...Array(50)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-1 h-1 bg-white rounded-full"
          style={{
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
            opacity: Math.random() * 0.5 + 0.3,
          }}
          animate={{
            opacity: [0.3, 0.8, 0.3],
            scale: [1, 1.5, 1],
          }}
          transition={{
            duration: 2 + Math.random() * 3,
            repeat: Infinity,
            delay: Math.random() * 2,
          }}
        />
      ))}
    </div>

    <EnergyParticles isActive={true} />
    <div className="relative z-10">
      {/* ... existing content ... */}
    </div>
  </div>
);
```

**Step 4: Update Chat.tsx**

**File:** `react-ui/src/pages/Chat.tsx`

```tsx
// REPLACE existing background layers (lines ~340-350)
return (
  <div className="flex h-full overflow-hidden relative">
    {/* Deep space background */}
    <div className="absolute inset-0 bg-space"></div>
    <div className="absolute inset-0 bg-nebula opacity-40"></div>

    {/* Rarity-based overlay (keeps persona theming) */}
    <div className={`absolute inset-0 bg-gradient-to-br ${colorScheme.bgGradient} opacity-20`}></div>

    {/* Character background (if exists) */}
    {personaBackground && (
      <div
        className="absolute inset-0 opacity-8 pointer-events-none"
        style={{
          backgroundImage: `url(${personaBackground})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
        }}
      />
    )}

    {/* White overlay for text readability */}
    <div className="absolute inset-0 bg-white bg-opacity-85"></div>

    <FloatingParticles isActive={loading || isSearching || input.length > 0} />

    {/* ... rest of component ... */}
  </div>
);
```

#### Testing Checklist

- [ ] Home page shows deep space background with stars
- [ ] Chat page shows space background + rarity overlay
- [ ] Background doesn't interfere with text readability
- [ ] Stars animate smoothly (60fps)
- [ ] Mobile devices render background correctly
- [ ] Background persists across navigation

---

### 1.3 Keyboard Navigation & Accessibility

**Estimated Time:** 2-3 hours
**Priority:** 🔥 Critical
**Files Modified:** `react-ui/src/components/CharacterCardV2.tsx`, `react-ui/src/components/MessageBubble.tsx`, `react-ui/src/index.css`
**Impact Score:** ⭐⭐⭐⭐⭐ (WCAG AA compliance)

#### Problem Statement
1. CharacterCardV2 uses `<motion.div>` → not keyboard accessible
2. Missing focus indicators on interactive elements
3. Color contrast failures (citations: gray-700 on gray-100 = 4.2:1, needs 4.5:1)
4. Screen reader context missing on technical info

#### Solution Design

**Accessibility Standards:**
- WCAG AA Level compliance
- Keyboard navigation for all interactive elements
- Focus indicators with 3px outline
- Minimum 4.5:1 color contrast for body text
- Screen reader announcements for all actions

#### Implementation Steps

**Step 1: Add Screen Reader Utility Class**

**File:** `react-ui/src/index.css`

```css
/* Add to utilities section */

/* Screen reader only text */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}

/* Focus visible styles */
*:focus-visible {
  outline: 3px solid var(--color-accent, #EC4899);
  outline-offset: 2px;
}

/* Skip to main content link */
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  background: #000;
  color: #fff;
  padding: 8px;
  text-decoration: none;
  z-index: 100;
}

.skip-link:focus {
  top: 0;
}
```

**Step 2: Fix CharacterCardV2 Keyboard Navigation**

**File:** `react-ui/src/components/CharacterCardV2.tsx`

```tsx
import React, { useRef, useState } from 'react';
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion';
import styles from './CharacterCardV2.module.css';

// ... interfaces ...

const CharacterCardV2: React.FC<CharacterCardV2Props> = ({
  name,
  style,
  image,
  rarity,
  onSelect,
  isSelected,
  personaKey,
  index = 0
}) => {
  // ... existing state ...
  const [isFocused, setIsFocused] = useState(false);

  // ... existing motion values ...

  const handleChooseClick = () => {
    onSelect(personaKey);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleChooseClick();
    }
  };

  return (
    <motion.button
      ref={cardRef}
      className={`${styles['card-outer']} ${rarityClass} ${selectedClass}`}
      style={{
        // ... existing styles ...
        outline: isFocused ? `3px solid ${colors.primary}` : 'none',
        outlineOffset: isFocused ? '4px' : '0',
      } as React.CSSProperties}
      onClick={handleChooseClick}
      onKeyPress={handleKeyPress}
      onFocus={() => setIsFocused(true)}
      onBlur={() => setIsFocused(false)}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      tabIndex={0}
      aria-label={`Select ${name}, ${rarity} rarity character. Style: ${style}.`}
      aria-pressed={isSelected}
      role="button"
      // ... existing props ...
    >
      {/* ... existing content ... */}
    </motion.button>
  );
};

export default CharacterCardV2;
```

**Step 3: Fix MessageBubble Color Contrast**

**File:** `react-ui/src/components/MessageBubble.tsx`

```tsx
// UPDATE citation section (line ~110)
{parsed.hasCitations && parsed.citationSection && (
  <div className="mt-4 pt-3 border-t border-gray-300/50">
    {/* CHANGE: text-gray-700 → text-gray-900 for WCAG AA compliance */}
    <RichContent content={parsed.citationSection} className="text-sm text-gray-900" />
  </div>
)}

// UPDATE latency display with screen reader context (line ~155)
{message.latency && (
  <span className="text-blue-400 font-mono text-xs">
    <span className="sr-only">Response time: </span>
    {message.latency < 1000
      ? `${message.latency}ms`
      : `${(message.latency / 1000).toFixed(1)}s`
    }
  </span>
)}

// UPDATE search badge with aria-label (line ~125)
{!isUser && message.used_search && (
  <div
    className="flex items-center gap-1.5 mt-3 pt-2 border-t border-gray-200/50"
    role="status"
    aria-label="This response includes web search results"
  >
    {/* ... existing content ... */}
  </div>
)}
```

**Step 4: Add Skip to Main Content**

**File:** `react-ui/src/App.tsx`

```tsx
function App() {
  return (
    <AudioProvider>
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <div className="App h-screen flex flex-col app-background">
        <Header />
        <main id="main-content" className="flex-1 overflow-auto relative z-10">
          <Routes>
            {/* ... routes ... */}
          </Routes>
        </main>
      </div>
    </AudioProvider>
  );
}
```

**Step 5: Update CharacterCardV2.module.css**

**File:** `react-ui/src/components/CharacterCardV2.module.css`

```css
/* Add focus styles */
.card-outer:focus-visible {
  outline: 3px solid var(--rarity-primary);
  outline-offset: 4px;
  box-shadow:
    0 0 0 6px rgba(0, 0, 0, 0.8),
    0 0 0 9px var(--rarity-glow);
}

/* Ensure button resets */
.card-outer {
  border: none;
  background: none;
  cursor: pointer;
  text-align: left;
  /* ... existing styles ... */
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  .card-outer {
    border: 2px solid currentColor;
  }

  .character-name,
  .character-style {
    text-shadow: none;
    color: #ffffff;
  }
}
```

#### Testing Checklist

**Keyboard Navigation:**
- [ ] Tab key cycles through all character cards
- [ ] Enter/Space selects focused card
- [ ] Focus indicator visible with 3px outline
- [ ] Skip link appears on Tab (before header)
- [ ] All buttons reachable via keyboard

**Screen Reader:**
- [ ] Character cards announce name, rarity, and style
- [ ] Selected state announced ("pressed")
- [ ] Latency values include "Response time" prefix
- [ ] Search indicators have role="status"

**Color Contrast:**
- [ ] Citations use gray-900 (13.1:1 contrast) ✅
- [ ] All body text meets 4.5:1 minimum
- [ ] Focus indicators have 3:1 contrast against background

**Tools for Testing:**
- Chrome DevTools Lighthouse (Accessibility audit)
- axe DevTools browser extension
- Keyboard only (unplug mouse)
- NVDA or JAWS screen reader (Windows)
- VoiceOver (macOS)

---

## Phase 2: High Impact Improvements

### 2.1 Message & Session Search

**Estimated Time:** 3-4 hours
**Priority:** ⚡ High Impact
**Files Modified:** `react-ui/src/components/SessionList.tsx`, `react-ui/src/pages/Chat.tsx`
**Impact Score:** ⭐⭐⭐⭐

#### Problem Statement
Users with 50+ sessions and 200+ messages per conversation have no way to search content. Current solution is manual scrolling or Ctrl+F (poor UX).

#### Solution Design

**Two-Tier Search System:**
1. **Global Session Search** (SessionList) - Filter sessions by title or persona name
2. **In-Conversation Search** (Chat) - Find specific messages within active session

**UX Patterns:**
- Collapsible search bars (don't clutter UI when unused)
- Real-time filtering (no "Search" button needed)
- Result count indicators
- Clear search button (X icon)
- Highlight matching text

#### Implementation Steps

**Step 1: Add Session Search**

**File:** `react-ui/src/components/SessionList.tsx`

```tsx
// Add to imports
import { Search, X } from 'lucide-react';

// Add state (after existing useState declarations)
const [searchQuery, setSearchQuery] = useState('');

// Add filtering logic (before return statement)
const filteredSessions = useMemo(() => {
  if (!searchQuery.trim()) return sessions;

  const query = searchQuery.toLowerCase();
  return sessions.filter(session => {
    const matchesTitle = session.title.toLowerCase().includes(query);
    const persona = getPersonaForSession(session.persona_key);
    const matchesPersona = persona?.display_name.toLowerCase().includes(query);
    return matchesTitle || matchesPersona;
  });
}, [sessions, searchQuery, personas]);

// UPDATE return JSX (replace current header + list)
return (
  <div className="w-80 bg-gradient-to-b from-slate-900/95 via-slate-800/95 to-slate-900/95 backdrop-blur-xl border-r border-slate-700/50 flex flex-col h-full relative overflow-hidden">
    {/* ... existing background layers ... */}

    {/* Header */}
    <div className="relative p-4 border-b border-slate-700/50">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold text-white drop-shadow-lg font-display">
          Chat History
        </h2>
        <span className="text-xs text-gray-400 font-mono">
          {filteredSessions.length}/{sessions.length}
        </span>
      </div>

      {/* Search Input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="search"
          placeholder="Search conversations..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-10 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg
                     focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent
                     text-white placeholder-gray-400 text-sm font-body
                     transition-all duration-200"
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery('')}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white
                       transition-colors"
            aria-label="Clear search"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* No results message */}
      {searchQuery && filteredSessions.length === 0 && (
        <p className="text-sm text-gray-400 mt-2 text-center font-body">
          No conversations found
        </p>
      )}
    </div>

    {/* Sessions List - use filteredSessions instead of sessions */}
    <div className="relative flex-1 overflow-y-auto p-2">
      {filteredSessions.length === 0 && !searchQuery ? (
        {/* ... existing empty state ... */}
      ) : (
        filteredSessions.map((session) => {
          {/* ... existing session rendering ... */}
        })
      )}
    </div>
  </div>
);
```

**Step 2: Add In-Conversation Search**

**File:** `react-ui/src/pages/Chat.tsx`

```tsx
// Add to imports
import { Search, X, ChevronUp, ChevronDown } from 'lucide-react';

// Add state (after existing useState declarations)
const [showMessageSearch, setShowMessageSearch] = useState(false);
const [messageSearchQuery, setMessageSearchQuery] = useState('');
const [searchResults, setSearchResults] = useState<number[]>([]);
const [currentResultIndex, setCurrentResultIndex] = useState(0);
const messageRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});

// Add search logic
useEffect(() => {
  if (!messageSearchQuery.trim()) {
    setSearchResults([]);
    setCurrentResultIndex(0);
    return;
  }

  const query = messageSearchQuery.toLowerCase();
  const results = messages.reduce((acc, msg, idx) => {
    if (msg.content.toLowerCase().includes(query)) {
      acc.push(idx);
    }
    return acc;
  }, [] as number[]);

  setSearchResults(results);
  setCurrentResultIndex(results.length > 0 ? 0 : -1);

  // Scroll to first result
  if (results.length > 0) {
    const firstResultId = messages[results[0]].id;
    messageRefs.current[firstResultId]?.scrollIntoView({
      behavior: 'smooth',
      block: 'center'
    });
  }
}, [messageSearchQuery, messages]);

// Navigation functions
const goToNextResult = () => {
  if (searchResults.length === 0) return;
  const nextIndex = (currentResultIndex + 1) % searchResults.length;
  setCurrentResultIndex(nextIndex);
  const messageId = messages[searchResults[nextIndex]].id;
  messageRefs.current[messageId]?.scrollIntoView({
    behavior: 'smooth',
    block: 'center'
  });
};

const goToPrevResult = () => {
  if (searchResults.length === 0) return;
  const prevIndex = (currentResultIndex - 1 + searchResults.length) % searchResults.length;
  setCurrentResultIndex(prevIndex);
  const messageId = messages[searchResults[prevIndex]].id;
  messageRefs.current[messageId]?.scrollIntoView({
    behavior: 'smooth',
    block: 'center'
  });
};

// UPDATE Header section (add search bar after title)
<div className="bg-white border-b border-gray-200 px-4 md:px-6 py-4 shadow-sm flex-shrink-0">
  <div className="flex justify-between items-center gap-3">
    {/* ... existing header content ... */}
  </div>

  {/* Search Bar (collapsible) */}
  <AnimatePresence>
    {showMessageSearch && (
      <motion.div
        initial={{ height: 0, opacity: 0 }}
        animate={{ height: 'auto', opacity: 1 }}
        exit={{ height: 0, opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="overflow-hidden"
      >
        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-200">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="search"
              placeholder="Search messages..."
              value={messageSearchQuery}
              onChange={(e) => setMessageSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg
                         focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm font-body"
              autoFocus
            />
          </div>

          {/* Results count */}
          {searchResults.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600 font-mono whitespace-nowrap">
                {currentResultIndex + 1}/{searchResults.length}
              </span>
              <button
                onClick={goToPrevResult}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                aria-label="Previous result"
              >
                <ChevronUp className="w-4 h-4" />
              </button>
              <button
                onClick={goToNextResult}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                aria-label="Next result"
              >
                <ChevronDown className="w-4 h-4" />
              </button>
            </div>
          )}

          <button
            onClick={() => {
              setShowMessageSearch(false);
              setMessageSearchQuery('');
            }}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label="Close search"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </motion.div>
    )}
  </AnimatePresence>

  {/* Search toggle button (in header actions) */}
  <button
    onClick={() => setShowMessageSearch(!showMessageSearch)}
    className="px-3 md:px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm md:text-base"
    title="Search messages"
  >
    <Search className="w-4 h-4" />
  </button>
</div>

// UPDATE MessageBubble rendering (add ref + highlight)
messages.map((msg, idx) => {
  const isHighlighted = searchResults.includes(idx);
  const isCurrentResult = searchResults[currentResultIndex] === idx;

  return (
    <div
      key={msg.id}
      ref={(el) => { messageRefs.current[msg.id] = el; }}
      className={`transition-all duration-300 ${
        isCurrentResult ? 'ring-4 ring-blue-400 rounded-2xl' :
        isHighlighted ? 'ring-2 ring-blue-200 rounded-2xl' : ''
      }`}
    >
      <MessageBubble
        message={msg}
        personaAvatar={selectedPersona.avatar ? `/images/${selectedPersona.avatar}` : `/images/${selectedPersona.image}`}
        userAvatar="/images/ui/user_avatar.png"
        showTimestamp={true}
        onRetry={handleRetryMessage}
        personaRarity={selectedPersona.rarity}
        personaName={selectedPersona.display_name}
      />
    </div>
  );
})
```

#### Testing Checklist

**Session Search:**
- [ ] Search filters sessions in real-time
- [ ] Matches both session title and persona name
- [ ] Shows "X/Y" result count
- [ ] Clear button (X) resets search
- [ ] Empty state shows "No conversations found"

**Message Search:**
- [ ] Search bar toggles open/closed
- [ ] Highlights all matching messages
- [ ] Current result has stronger highlight (ring-4)
- [ ] Prev/Next buttons navigate results
- [ ] Counter shows "1/N" format
- [ ] Scrolls to results smoothly
- [ ] Closes with X button

---

### 2.2 Button Hierarchy & User Flows

**Estimated Time:** 1 hour
**Priority:** ⚡ High Impact
**Files Modified:** `react-ui/src/pages/Home.tsx`, `react-ui/src/pages/Chat.tsx`
**Impact Score:** ⭐⭐⭐⭐

#### Problem Statement
1. Home.tsx: Primary and secondary CTAs look identical
2. Chat.tsx: No clear "Change Character" button
3. Pull result flow doesn't preserve pulled characters

#### Solution Design

**Visual Hierarchy Principles:**
- Primary CTA: Largest, solid gradient, prominent shadow
- Secondary CTA: Smaller, outlined style, subtle hover
- Tertiary: Text link or icon button

#### Implementation Steps

**Step 1: Fix Home Page Button Hierarchy**

**File:** `react-ui/src/pages/Home.tsx`

```tsx
// REPLACE existing button section (lines ~40-65)
<div className="flex flex-col gap-4 items-center w-full max-w-md">
  {/* Primary CTA - Gacha Pull */}
  <motion.button
    className="w-full px-10 py-5 text-xl font-bold font-display uppercase tracking-wide
               bg-gradient-to-r from-yellow-400 via-orange-500 to-yellow-400
               text-black rounded-2xl
               shadow-2xl shadow-yellow-400/50
               relative overflow-hidden group"
    onClick={handlePullCharacter}
    whileHover={{ scale: 1.03, y: -2 }}
    whileTap={{ scale: 0.98 }}
    transition={{ type: 'spring', stiffness: 400, damping: 25 }}
  >
    {/* Animated shine effect */}
    <motion.div
      className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent"
      animate={{ x: ['-200%', '200%'] }}
      transition={{ duration: 2, repeat: Infinity, ease: 'linear', repeatDelay: 1 }}
    />
    <span className="relative z-10 flex items-center justify-center gap-3">
      <span className="text-2xl">🎲</span>
      <span>Try Your Luck</span>
    </span>
  </motion.button>

  {/* Secondary CTA - Browse */}
  <motion.button
    className="w-full px-6 py-3 text-base font-semibold font-body
               border-2 border-yellow-400/50 text-yellow-400
               rounded-xl
               hover:bg-yellow-400/10 hover:border-yellow-400
               transition-all duration-200"
    onClick={handleBrowseCollection}
    whileHover={{ scale: 1.02 }}
    whileTap={{ scale: 0.98 }}
  >
    <span className="flex items-center justify-center gap-2">
      <span>📚</span>
      <span>Browse All Agents</span>
    </span>
  </motion.button>

  {/* Tertiary - Collection Link */}
  <a
    href="/collection"
    className="text-gray-400 hover:text-white transition-colors text-sm font-body underline"
  >
    View My Collection →
  </a>
</div>
```

**Step 2: Add "Change Character" Button**

**File:** `react-ui/src/pages/Chat.tsx`

```tsx
// UPDATE header section (add after title, before export/import buttons)
<div className="flex justify-between items-center gap-3 mb-2">
  <div className="flex items-center gap-3 min-w-0 flex-1">
    {/* ... existing sidebar toggle and title ... */}
  </div>

  {/* Change Character Button */}
  <Link
    to="/select"
    className="flex items-center gap-2 px-4 py-2
               bg-purple-500/20 border border-purple-400/50
               rounded-lg hover:bg-purple-500/30
               transition-all duration-200 text-purple-400 hover:text-purple-300
               text-sm font-medium font-body
               hidden md:flex"
  >
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
    </svg>
    <span>Change Character</span>
  </Link>

  {/* Mobile: Icon only */}
  <Link
    to="/select"
    className="md:hidden p-2 bg-purple-500/20 border border-purple-400/50 rounded-lg
               text-purple-400 hover:bg-purple-500/30 transition-colors"
    title="Change Character"
  >
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
    </svg>
  </Link>
</div>

{/* Session actions row */}
{currentSession && (
  <div className="flex gap-1 md:gap-2 flex-shrink-0 mt-2">
    {/* ... existing export/import/clear buttons ... */}
  </div>
)}
```

**Step 3: Fix Pull Result Flow**

**File:** `react-ui/src/components/PullInterface.tsx`

```tsx
// UPDATE handleCharacterSelect function (line ~80)
const handleCharacterSelect = (personaKey: string) => {
  // ADD: Auto-add to collection before selecting
  addToCollection(personaKey);
  onCharacterSelect(personaKey);
  // Reset for next pull
  setPulledCharacter(null);
  setShowResult(false);
  setPullStage('idle');
};

// UPDATE action buttons section (line ~415)
<motion.div
  initial={{ y: 20, opacity: 0 }}
  animate={{ y: 0, opacity: 1 }}
  transition={{ delay: 1.5 }}
  className="flex flex-col sm:flex-row gap-4 justify-center w-full max-w-md"
>
  {/* Primary: Start chatting */}
  <motion.button
    onClick={() => handleCharacterSelect(pulledCharacter!.key)}
    className="flex-1 px-8 py-4 bg-gradient-to-r from-blue-500 to-purple-600
               text-white font-bold font-display rounded-2xl
               shadow-lg hover:shadow-xl transition-all duration-300"
    whileHover={{ scale: 1.05, y: -2 }}
    whileTap={{ scale: 0.95 }}
  >
    Start Chatting
  </motion.button>

  {/* Secondary: Pull again */}
  <motion.button
    onClick={() => {
      addToCollection(pulledCharacter!.key); // PRESERVE character
      setPulledCharacter(null);
      setShowResult(false);
      setPullStage('idle');
    }}
    className="flex-1 px-8 py-4 border-2 border-gray-500 text-white
               font-semibold font-body rounded-2xl
               hover:bg-gray-500/20 transition-all duration-300"
    whileHover={{ scale: 1.02 }}
    whileTap={{ scale: 0.95 }}
  >
    Pull Again
  </motion.button>
</motion.div>
```

#### Testing Checklist

- [ ] Home: Primary button larger, has shine animation
- [ ] Home: Secondary button uses outlined style
- [ ] Home: Collection link is subtle text link
- [ ] Chat: "Change Character" visible on desktop
- [ ] Chat: Icon-only button on mobile
- [ ] Pull: "Start Chatting" is primary style
- [ ] Pull: "Pull Again" adds character to collection first

---

### 2.3 Animation Performance Optimization

**Estimated Time:** 2-3 hours
**Priority:** ⚡ High Impact
**Files Modified:** Multiple component files, `react-ui/src/utils/animations.ts`
**Impact Score:** ⭐⭐⭐⭐

#### Problem Statement
Too many simultaneous animations risk dropping below 60fps, especially on:
- Chat.tsx: 3 background layers + 8 particles + session list + messages
- Pull interface: 50+ celebration particles
- No standardized timing system

#### Solution Design

**Optimization Strategies:**
1. Create animation constants for consistency
2. Use `will-change` only during active animation
3. Reduce concurrent animations (disable particles during transitions)
4. Implement performance monitoring
5. Add reduced-motion support

#### Implementation Steps

**Step 1: Create Animation System**

**File:** `react-ui/src/utils/animations.ts` (NEW FILE)

```typescript
/**
 * Standardized Animation System
 * Provides consistent timing, easing, and spring configs across the app
 */

// Duration constants (seconds)
export const ANIMATION_DURATIONS = {
  instant: 0.1,     // Instant feedback (tooltips, micro-interactions)
  fast: 0.2,        // Fast transitions (button hovers, toggles)
  normal: 0.3,      // Default transitions (most UI elements)
  slow: 0.5,        // Deliberate transitions (modals, page changes)
  dramatic: 0.8,    // Dramatic reveals (gacha pulls, celebrations)
  epic: 1.2,        // Epic moments (legendary character reveals)
} as const;

// Easing functions
export const EASINGS = {
  linear: [0, 0, 1, 1],
  easeIn: [0.4, 0, 1, 1],
  easeOut: [0, 0, 0.2, 1],
  easeInOut: [0.4, 0, 0.2, 1],
  spring: [0.5, 1, 0.89, 1],
} as const;

// Spring configurations
export const SPRING_CONFIGS = {
  // Snappy: Quick, tight response (buttons, cards)
  snappy: {
    type: 'spring' as const,
    stiffness: 400,
    damping: 25,
  },

  // Smooth: Balanced, natural feel (default)
  smooth: {
    type: 'spring' as const,
    stiffness: 300,
    damping: 30,
  },

  // Bouncy: Playful, energetic (celebrations, reveals)
  bouncy: {
    type: 'spring' as const,
    stiffness: 200,
    damping: 15,
  },

  // Gentle: Soft, gradual (large elements, backgrounds)
  gentle: {
    type: 'spring' as const,
    stiffness: 150,
    damping: 20,
  },
} as const;

// Stagger configurations
export const STAGGER = {
  fast: 0.05,     // Rapid sequential (list items)
  normal: 0.1,    // Default stagger (cards, messages)
  slow: 0.2,      // Dramatic stagger (hero elements)
} as const;

/**
 * Performance utilities
 */

// Check if user prefers reduced motion
export const prefersReducedMotion = (): boolean => {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
};

// Conditional animation: returns static values if reduced motion preferred
export function conditionalAnimation<T>(animatedValue: T, staticValue: T): T {
  return prefersReducedMotion() ? staticValue : animatedValue;
}

// Will-change helper: only apply during animation
export const useWillChange = (isAnimating: boolean, properties: string[]): string => {
  return isAnimating ? properties.join(', ') : 'auto';
};

/**
 * Common animation variants
 */

export const FADE_VARIANTS = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { duration: ANIMATION_DURATIONS.normal }
  },
};

export const SLIDE_UP_VARIANTS = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: SPRING_CONFIGS.smooth,
  },
};

export const SCALE_VARIANTS = {
  hidden: { opacity: 0, scale: 0.9 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: SPRING_CONFIGS.snappy,
  },
};

export const STAGGER_CONTAINER_VARIANTS = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: STAGGER.normal,
    },
  },
};

/**
 * Performance monitoring (development only)
 */
export const measureAnimationPerformance = (name: string, callback: () => void) => {
  if (process.env.NODE_ENV !== 'development') {
    callback();
    return;
  }

  const start = performance.now();
  callback();
  const end = performance.now();

  const duration = end - start;
  if (duration > 16.67) { // 60fps threshold
    console.warn(`⚠️ Animation "${name}" took ${duration.toFixed(2)}ms (>16.67ms target)`);
  }
};
```

**Step 2: Update Chat.tsx**

**File:** `react-ui/src/pages/Chat.tsx`

```tsx
// Add import
import { SPRING_CONFIGS, ANIMATION_DURATIONS, conditionalAnimation } from '../utils/animations';

// UPDATE FloatingParticles component
const FloatingParticles: React.FC<{ isActive: boolean }> = React.memo(({ isActive }) => {
  const particles = React.useMemo(() => {
    return Array.from({ length: 8 }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      top: Math.random() * 100,
      xOffset: Math.random() * 10 - 5,
      duration: 3 + Math.random() * 2,
      delay: Math.random() * 2,
    }));
  }, []);

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((particle) => (
        <motion.div
          key={particle.id}
          className="absolute w-1.5 h-1.5 bg-white/30 rounded-full shadow-sm"
          style={{
            left: `${particle.left}%`,
            top: `${particle.top}%`,
            // Only use will-change when animating
            willChange: isActive ? 'transform, opacity' : 'auto',
          }}
          animate={conditionalAnimation(
            isActive ? {
              y: [0, -20, 0],
              x: [0, particle.xOffset, 0],
              opacity: [0.2, 0.6, 0.2],
              scale: [0.6, 1.0, 0.6],
            } : {
              opacity: 0.1,
              scale: 0.6,
            },
            { opacity: 0.1, scale: 0.6 } // Static fallback
          )}
          transition={{
            duration: particle.duration,
            repeat: isActive ? Infinity : 0,
            delay: particle.delay,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
});

// UPDATE particle activation (reduce concurrent animations)
<FloatingParticles isActive={loading && !isSidebarOpen && !isSearching} />

// UPDATE sidebar animation
<motion.div
  initial={{ x: -320 }}
  animate={{
    x: isSidebarOpen ? 0 : -320,
    width: 320
  }}
  transition={SPRING_CONFIGS.smooth}
  className="fixed z-50 h-full"
>
  <SessionList onSessionSelect={handleSessionSelect} />
</motion.div>

// UPDATE input animation
<motion.input
  // ... existing props ...
  whileFocus={{ scale: 1.01 }}
  transition={SPRING_CONFIGS.snappy}
/>

// UPDATE send button
<motion.button
  // ... existing props ...
  whileHover={{ scale: 1.05 }}
  whileTap={{ scale: 0.95 }}
  transition={SPRING_CONFIGS.snappy}
/>
```

**Step 3: Update CharacterCardV2**

**File:** `react-ui/src/components/CharacterCardV2.tsx`

```tsx
// Add import
import { SPRING_CONFIGS, ANIMATION_DURATIONS } from '../utils/animations';

// UPDATE motion values (only use will-change when hovering)
<motion.div
  ref={cardRef}
  className={`${styles['card-outer']} ${rarityClass} ${selectedClass}`}
  style={{
    '--rarity-primary': colors.primary,
    '--rarity-secondary': colors.secondary,
    '--rarity-glow': colors.glow,
    '--rarity-gradient': colors.gradient,
    rotateX: isHovered ? rotateX : 0,
    rotateY: isHovered ? rotateY : 0,
    transformStyle: 'preserve-3d',
    transformOrigin: 'center center',
    willChange: isHovered ? 'transform' : 'auto', // Only during hover
  } as React.CSSProperties}
  initial={{ opacity: 0, y: 20, scale: 0.9 }}
  animate={{ opacity: 1, y: 0, scale: 1 }}
  transition={{
    ...SPRING_CONFIGS.smooth,
    delay: index * 0.1
  }}
  whileHover={{
    y: -8,
    scale: 1.03,
    transition: SPRING_CONFIGS.snappy
  }}
  whileTap={{ scale: 0.98 }}
  onMouseMove={handleMouseMove}
  onMouseEnter={handleMouseEnter}
  onMouseLeave={handleMouseLeave}
>
```

**Step 4: Update PullInterface**

**File:** `react-ui/src/components/PullInterface.tsx`

```tsx
// Add import
import { ANIMATION_DURATIONS, SPRING_CONFIGS } from '../utils/animations';

// REDUCE celebration particles (50 → 30 for better performance)
{pulledCharacter.rarity === 'legendary' && (
  <>
    {/* ... existing sparkle effect ... */}

    {/* REDUCE from 20 to 12 particles */}
    {[...Array(12)].map((_, i) => (
      <motion.div
        key={i}
        initial={{ x: '50vw', y: '50vh', scale: 0, opacity: 0 }}
        animate={{
          x: `${50 + (Math.random() - 0.5) * 100}vw`,
          y: `${50 + (Math.random() - 0.5) * 100}vh`,
          scale: [0, 1, 0],
          opacity: [0, 1, 0],
          rotate: [0, 360]
        }}
        transition={{
          duration: ANIMATION_DURATIONS.dramatic,
          delay: 1.5 + i * 0.08, // Stagger
          ease: "easeOut"
        }}
        className="absolute w-4 h-4 text-yellow-400"
        style={{ willChange: 'transform, opacity' }} // Explicit will-change
      >
        {['✨', '⭐', '🎊'][Math.floor(Math.random() * 3)]}
      </motion.div>
    ))}
  </>
)}

// UPDATE pull button animation timing
<motion.button
  // ... existing props ...
  animate={pullStage === 'building' ? {
    scale: [1, 1.1, 1],
    boxShadow: [
      '0 25px 50px -12px rgba(251, 191, 36, 0.25)',
      '0 25px 50px -12px rgba(251, 191, 36, 0.5)',
      '0 25px 50px -12px rgba(251, 191, 36, 0.25)'
    ]
  } : {}}
  transition={{
    duration: pullStage === 'building' ? 0.8 : ANIMATION_DURATIONS.normal,
    repeat: pullStage === 'building' ? Infinity : 0,
    ease: "easeInOut"
  }}
  whileHover={!isPulling ? { scale: 1.05 } : {}}
  whileTap={!isPulling ? { scale: 0.95 } : {}}
>
```

**Step 5: Add Performance Monitoring (Development)**

**File:** `react-ui/src/index.tsx`

```tsx
// Add after imports
if (process.env.NODE_ENV === 'development') {
  // Monitor frame rate
  let lastTime = performance.now();
  let frames = 0;
  let fps = 60;

  function measureFPS() {
    const currentTime = performance.now();
    frames++;

    if (currentTime >= lastTime + 1000) {
      fps = Math.round((frames * 1000) / (currentTime - lastTime));
      if (fps < 55) {
        console.warn(`⚠️ Low FPS detected: ${fps} fps (target: 60 fps)`);
      }
      frames = 0;
      lastTime = currentTime;
    }

    requestAnimationFrame(measureFPS);
  }

  requestAnimationFrame(measureFPS);
}
```

#### Testing Checklist

**Performance:**
- [ ] Open Chrome DevTools → Performance tab
- [ ] Record 10-second interaction (navigate, hover cards, pull character)
- [ ] Check FPS stays above 55fps during animations
- [ ] Verify CPU usage < 50% on mid-range devices

**Animation Consistency:**
- [ ] All buttons use SPRING_CONFIGS.snappy
- [ ] All page transitions use SPRING_CONFIGS.smooth
- [ ] Durations match ANIMATION_DURATIONS constants
- [ ] `will-change` only appears during active animation (inspect element)

**Reduced Motion:**
- [ ] Set OS to prefer reduced motion
- [ ] Verify particles don't animate
- [ ] Verify 3D transforms disabled
- [ ] Core functionality still works

**Tools:**
- Chrome DevTools Performance tab
- React DevTools Profiler
- Lighthouse performance audit

---

## Phase 3: Nice to Have

### 3.1 Stats & Analytics Page

**Estimated Time:** 4-6 hours
**Priority:** 💎 Nice to Have
**Files Created:** `react-ui/src/pages/Stats.tsx`, `react-ui/src/services/statsApi.ts`
**Impact Score:** ⭐⭐⭐

#### Problem Statement
Users can't see aggregate data about their conversations:
- Which persona they chat with most
- Average response times per persona
- Total message counts
- Collection completion percentage

#### Solution Design

**Page Structure:**
1. **Overview Cards** - Total stats (sessions, messages, avg latency)
2. **Persona Rankings** - Grid of persona cards with usage stats
3. **Collection Progress** - Visual progress bar showing X/Y personas collected
4. **Timeline Chart** - Messages per day (last 30 days)

#### Implementation Steps

**Step 1: Create Stats Service**

**File:** `react-ui/src/services/statsApi.ts` (NEW FILE)

```typescript
import { ChatSession, Message } from './api';

export interface PersonaStats {
  personaKey: string;
  displayName: string;
  rarity: string;
  avatar?: string;
  sessionCount: number;
  messageCount: number;
  avgLatency: number;
  lastUsed: Date;
}

export interface OverallStats {
  totalSessions: number;
  totalMessages: number;
  totalPersonas: number;
  collectedPersonas: number;
  avgLatency: number;
  mostUsedPersona: string;
}

export interface TimelineData {
  date: string;
  messageCount: number;
}

export function calculatePersonaStats(
  sessions: ChatSession[],
  messages: { [sessionId: string]: Message[] },
  personas: any[]
): PersonaStats[] {
  const statsMap = new Map<string, PersonaStats>();

  // Aggregate session and message data
  sessions.forEach(session => {
    const sessionMessages = messages[session.id] || [];
    const assistantMessages = sessionMessages.filter(m => m.role === 'assistant');
    const avgLatency = assistantMessages.reduce((sum, m) => sum + (m.latency || 0), 0) / assistantMessages.length || 0;

    const existing = statsMap.get(session.persona_key);
    if (existing) {
      existing.sessionCount++;
      existing.messageCount += sessionMessages.length;
      existing.avgLatency = (existing.avgLatency + avgLatency) / 2;
      existing.lastUsed = new Date(Math.max(existing.lastUsed.getTime(), new Date(session.updated_at).getTime()));
    } else {
      const persona = personas.find(p => p.key === session.persona_key);
      if (persona) {
        statsMap.set(session.persona_key, {
          personaKey: session.persona_key,
          displayName: persona.display_name,
          rarity: persona.rarity,
          avatar: persona.avatar,
          sessionCount: 1,
          messageCount: sessionMessages.length,
          avgLatency,
          lastUsed: new Date(session.updated_at),
        });
      }
    }
  });

  return Array.from(statsMap.values()).sort((a, b) => b.messageCount - a.messageCount);
}

export function calculateOverallStats(
  sessions: ChatSession[],
  personaStats: PersonaStats[],
  totalPersonas: number
): OverallStats {
  const totalMessages = personaStats.reduce((sum, p) => sum + p.messageCount, 0);
  const avgLatency = personaStats.reduce((sum, p) => sum + p.avgLatency, 0) / personaStats.length || 0;
  const mostUsed = personaStats.length > 0 ? personaStats[0].displayName : 'None';

  return {
    totalSessions: sessions.length,
    totalMessages,
    totalPersonas,
    collectedPersonas: personaStats.length,
    avgLatency,
    mostUsedPersona: mostUsed,
  };
}

export function calculateTimeline(
  messages: { [sessionId: string]: Message[] },
  days: number = 30
): TimelineData[] {
  const now = new Date();
  const timeline: TimelineData[] = [];

  // Initialize dates
  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    timeline.push({
      date: date.toISOString().split('T')[0],
      messageCount: 0,
    });
  }

  // Count messages per day
  Object.values(messages).flat().forEach(msg => {
    if (!msg.timestamp) return;
    const msgDate = new Date(msg.timestamp).toISOString().split('T')[0];
    const entry = timeline.find(t => t.date === msgDate);
    if (entry) entry.messageCount++;
  });

  return timeline;
}
```

**Step 2: Create Stats Page**

**File:** `react-ui/src/pages/Stats.tsx` (NEW FILE)

```tsx
import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { usePersona } from '../context/PersonaContext';
import { calculatePersonaStats, calculateOverallStats, calculateTimeline } from '../services/statsApi';
import { MessageSquare, Users, Clock, TrendingUp, Award } from 'lucide-react';
import { SPRING_CONFIGS, SLIDE_UP_VARIANTS } from '../utils/animations';

const Stats: React.FC = () => {
  const { sessions, personas, /* need to add messages to context */ } = usePersona();

  // Calculate stats
  const personaStats = useMemo(() =>
    calculatePersonaStats(sessions, {/* messages */}, personas),
    [sessions, personas]
  );

  const overallStats = useMemo(() =>
    calculateOverallStats(sessions, personaStats, personas.length),
    [sessions, personaStats, personas]
  );

  const timeline = useMemo(() =>
    calculateTimeline({/* messages */}),
    [/* messages */]
  );

  const collectionProgress = (overallStats.collectedPersonas / overallStats.totalPersonas) * 100;

  return (
    <div className="min-h-screen app-background p-6">
      <div className="max-w-7xl mx-auto relative z-10">
        {/* Header */}
        <motion.div
          className="mb-8"
          variants={SLIDE_UP_VARIANTS}
          initial="hidden"
          animate="visible"
        >
          <h1 className="text-4xl font-display font-black text-white mb-2">
            Your Statistics
          </h1>
          <p className="text-gray-400 font-body">
            Track your conversations and persona usage
          </p>
        </motion.div>

        {/* Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard
            icon={<MessageSquare />}
            label="Total Messages"
            value={overallStats.totalMessages.toLocaleString()}
            color="blue"
          />
          <StatCard
            icon={<Users />}
            label="Conversations"
            value={overallStats.totalSessions.toLocaleString()}
            color="purple"
          />
          <StatCard
            icon={<Clock />}
            label="Avg Response Time"
            value={`${overallStats.avgLatency.toFixed(0)}ms`}
            color="green"
          />
          <StatCard
            icon={<Award />}
            label="Collection Progress"
            value={`${overallStats.collectedPersonas}/${overallStats.totalPersonas}`}
            color="yellow"
          />
        </div>

        {/* Collection Progress Bar */}
        <motion.div
          className="bg-card backdrop-blur-lg rounded-2xl p-6 mb-8 border border-white/10"
          variants={SLIDE_UP_VARIANTS}
          initial="hidden"
          animate="visible"
          transition={{ delay: 0.2 }}
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-display font-bold text-white">
              Collection Progress
            </h2>
            <span className="text-2xl font-mono text-yellow-400">
              {collectionProgress.toFixed(0)}%
            </span>
          </div>
          <div className="w-full h-4 bg-slate-800 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-yellow-400 via-orange-500 to-yellow-400"
              initial={{ width: 0 }}
              animate={{ width: `${collectionProgress}%` }}
              transition={{ duration: 1, ease: 'easeOut', delay: 0.5 }}
            />
          </div>
        </motion.div>

        {/* Persona Rankings */}
        <motion.div
          className="mb-8"
          variants={SLIDE_UP_VARIANTS}
          initial="hidden"
          animate="visible"
          transition={{ delay: 0.3 }}
        >
          <h2 className="text-2xl font-display font-bold text-white mb-4">
            Persona Usage
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {personaStats.map((stat, idx) => (
              <PersonaStatCard key={stat.personaKey} stat={stat} rank={idx + 1} />
            ))}
          </div>
        </motion.div>

        {/* Timeline Chart (simplified - could use recharts for better viz) */}
        <motion.div
          className="bg-card backdrop-blur-lg rounded-2xl p-6 border border-white/10"
          variants={SLIDE_UP_VARIANTS}
          initial="hidden"
          animate="visible"
          transition={{ delay: 0.4 }}
        >
          <h2 className="text-xl font-display font-bold text-white mb-4">
            Activity Timeline (Last 30 Days)
          </h2>
          <div className="flex items-end gap-1 h-40">
            {timeline.map((day, idx) => {
              const maxMessages = Math.max(...timeline.map(d => d.messageCount));
              const height = maxMessages > 0 ? (day.messageCount / maxMessages) * 100 : 0;

              return (
                <motion.div
                  key={day.date}
                  className="flex-1 bg-gradient-to-t from-blue-500 to-purple-600 rounded-t-md
                             hover:from-blue-400 hover:to-purple-500 transition-colors cursor-pointer"
                  style={{ height: `${height}%`, minHeight: day.messageCount > 0 ? '4px' : '0' }}
                  initial={{ height: 0 }}
                  animate={{ height: `${height}%` }}
                  transition={{ delay: 0.5 + idx * 0.01, duration: 0.3 }}
                  title={`${day.date}: ${day.messageCount} messages`}
                />
              );
            })}
          </div>
          <div className="flex justify-between mt-2 text-xs text-gray-400 font-mono">
            <span>30 days ago</span>
            <span>Today</span>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

// Stat Card Component
interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: 'blue' | 'purple' | 'green' | 'yellow';
}

const StatCard: React.FC<StatCardProps> = ({ icon, label, value, color }) => {
  const colorClasses = {
    blue: 'from-blue-500 to-cyan-600',
    purple: 'from-purple-500 to-violet-600',
    green: 'from-green-500 to-emerald-600',
    yellow: 'from-yellow-500 to-amber-600',
  };

  return (
    <motion.div
      className="bg-card backdrop-blur-lg rounded-xl p-6 border border-white/10"
      variants={SLIDE_UP_VARIANTS}
      whileHover={{ y: -4, transition: SPRING_CONFIGS.snappy }}
    >
      <div className={`inline-flex p-3 rounded-lg bg-gradient-to-br ${colorClasses[color]} mb-4`}>
        {React.cloneElement(icon as React.ReactElement, { className: 'w-6 h-6 text-white' })}
      </div>
      <div className="text-3xl font-display font-black text-white mb-1">
        {value}
      </div>
      <div className="text-sm text-gray-400 font-body">
        {label}
      </div>
    </motion.div>
  );
};

// Persona Stat Card Component
interface PersonaStatCardProps {
  stat: any;
  rank: number;
}

const PersonaStatCard: React.FC<PersonaStatCardProps> = ({ stat, rank }) => {
  const rarityColors = {
    legendary: 'from-yellow-500 to-amber-600',
    epic: 'from-purple-500 to-violet-600',
    rare: 'from-blue-500 to-cyan-600',
    common: 'from-gray-500 to-slate-600',
  };

  return (
    <motion.div
      className="bg-card backdrop-blur-lg rounded-xl p-4 border border-white/10 relative overflow-hidden"
      whileHover={{ y: -4, transition: SPRING_CONFIGS.snappy }}
    >
      {/* Rank Badge */}
      {rank <= 3 && (
        <div className="absolute top-2 right-2">
          <div className={`w-8 h-8 rounded-full bg-gradient-to-br ${
            rank === 1 ? 'from-yellow-400 to-amber-500' :
            rank === 2 ? 'from-gray-300 to-gray-400' :
            'from-orange-400 to-orange-600'
          } flex items-center justify-center font-display font-black text-black text-sm`}>
            #{rank}
          </div>
        </div>
      )}

      <div className="flex items-center gap-3 mb-4">
        {stat.avatar && (
          <img
            src={`/images/${stat.avatar}`}
            alt={stat.displayName}
            className="w-12 h-12 rounded-lg object-cover"
          />
        )}
        <div className="flex-1">
          <h3 className="text-lg font-display font-bold text-white">
            {stat.displayName}
          </h3>
          <span className={`text-xs px-2 py-0.5 rounded-full bg-gradient-to-r ${
            rarityColors[stat.rarity as keyof typeof rarityColors]
          } text-white font-medium`}>
            {stat.rarity}
          </span>
        </div>
      </div>

      <div className="space-y-2 text-sm">
        <div className="flex justify-between text-gray-300 font-body">
          <span>Messages:</span>
          <span className="font-mono font-semibold text-white">{stat.messageCount}</span>
        </div>
        <div className="flex justify-between text-gray-300 font-body">
          <span>Sessions:</span>
          <span className="font-mono font-semibold text-white">{stat.sessionCount}</span>
        </div>
        <div className="flex justify-between text-gray-300 font-body">
          <span>Avg Latency:</span>
          <span className="font-mono font-semibold text-white">{stat.avgLatency.toFixed(0)}ms</span>
        </div>
      </div>
    </motion.div>
  );
};

export default Stats;
```

**Step 3: Add Route**

**File:** `react-ui/src/App.tsx`

```tsx
import Stats from './pages/Stats';

// Add route
<Route path="/stats" element={<Stats />} />
```

**Step 4: Add Navigation Link**

**File:** `react-ui/src/components/header/HeaderNavigation.tsx`

```tsx
// Add to desktop navigation
<Link
  to="/stats"
  className="nav-link text-gray-300 hover:text-white transition-colors font-body"
>
  Stats
</Link>
```

#### Testing Checklist

- [ ] Stats page calculates totals correctly
- [ ] Persona rankings sort by message count
- [ ] Collection progress bar animates to correct percentage
- [ ] Timeline chart shows last 30 days
- [ ] Top 3 personas show rank badges
- [ ] Cards animate on scroll/load
- [ ] Mobile layout stacks correctly

---

### 3.2 Focus Trap & Modal Management

**Estimated Time:** 2 hours
**Priority:** 💎 Nice to Have
**Files Modified:** `react-ui/src/components/SessionList.tsx`, `react-ui/src/components/header/MobileMenu.tsx`
**Dependencies:** `focus-trap-react` package
**Impact Score:** ⭐⭐⭐

#### Problem Statement
When sidebar or mobile menu opens, keyboard focus can escape to background content, violating WCAG AA 2.4.3 (Focus Order).

#### Solution Design

**Focus Trap Requirements:**
1. Focus moves to first interactive element when modal opens
2. Tab cycling stays within modal
3. Esc key closes modal
4. Focus returns to trigger element when closed

#### Implementation Steps

**Step 1: Install Dependencies**

```bash
cd react-ui
npm install focus-trap-react --save
```

**Step 2: Update SessionList**

**File:** `react-ui/src/components/SessionList.tsx`

```tsx
import FocusTrap from 'focus-trap-react';
import { useRef, useEffect } from 'react';

// Add props
interface SessionListProps {
  onSessionSelect: (session: ChatSession) => void;
  isOpen?: boolean; // NEW
  onClose?: () => void; // NEW
}

const SessionList: React.FC<SessionListProps> = ({
  onSessionSelect,
  isOpen = true,
  onClose
}) => {
  const firstFocusableRef = useRef<HTMLInputElement>(null);

  // Focus search input when opened
  useEffect(() => {
    if (isOpen && firstFocusableRef.current) {
      firstFocusableRef.current.focus();
    }
  }, [isOpen]);

  // Handle Esc key
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && onClose) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEsc);
    }

    return () => document.removeEventListener('keydown', handleEsc);
  }, [isOpen, onClose]);

  return (
    <FocusTrap active={isOpen}>
      <div className="w-80 bg-gradient-to-b from-slate-900/95 via-slate-800/95 to-slate-900/95 backdrop-blur-xl border-r border-slate-700/50 flex flex-col h-full relative overflow-hidden">
        {/* ... existing content ... */}

        {/* UPDATE search input to be first focusable */}
        <input
          ref={firstFocusableRef}
          type="search"
          placeholder="Search conversations..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-10 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg
                     focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent
                     text-white placeholder-gray-400 text-sm font-body"
          aria-label="Search conversations"
        />

        {/* ... rest of component ... */}
      </div>
    </FocusTrap>
  );
};
```

**Step 3: Update Chat.tsx Sidebar**

**File:** `react-ui/src/pages/Chat.tsx`

```tsx
// UPDATE SessionList usage
<SessionList
  onSessionSelect={handleSessionSelect}
  isOpen={isSidebarOpen}
  onClose={() => setIsSidebarOpen(false)}
/>
```

**Step 4: Update MobileMenu**

**File:** `react-ui/src/components/header/MobileMenu.tsx`

```tsx
import FocusTrap from 'focus-trap-react';

export const MobileMenu: React.FC<MobileMenuProps> = ({
  isMobileMenuOpen,
  setIsMobileMenuOpen,
  // ... other props
}) => {
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (isMobileMenuOpen && closeButtonRef.current) {
      closeButtonRef.current.focus();
    }
  }, [isMobileMenuOpen]);

  const handleClose = () => {
    setIsMobileMenuOpen(false);
  };

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        handleClose();
      }
    };

    if (isMobileMenuOpen) {
      document.addEventListener('keydown', handleEsc);
    }

    return () => document.removeEventListener('keydown', handleEsc);
  }, [isMobileMenuOpen]);

  return (
    <AnimatePresence>
      {isMobileMenuOpen && (
        <FocusTrap active={isMobileMenuOpen}>
          <div>
            {/* Backdrop */}
            <motion.div
              className="fixed inset-0 bg-black/80 backdrop-blur-sm z-40"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={handleClose}
            />

            {/* Menu */}
            <motion.div
              className="fixed inset-y-0 right-0 w-80 max-w-full bg-slate-900 z-50 p-6"
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
            >
              {/* Close button - first focusable */}
              <button
                ref={closeButtonRef}
                onClick={handleClose}
                className="absolute top-4 right-4 p-2 text-white hover:bg-white/10 rounded-lg"
                aria-label="Close menu"
              >
                <X className="w-6 h-6" />
              </button>

              {/* Navigation links */}
              <nav className="mt-12 flex flex-col gap-4">
                {/* ... nav items ... */}
              </nav>
            </motion.div>
          </div>
        </FocusTrap>
      )}
    </AnimatePresence>
  );
};
```

#### Testing Checklist

**Focus Trap:**
- [ ] Tab key stays within modal when open
- [ ] Shift+Tab works in reverse
- [ ] Esc key closes modal
- [ ] Focus returns to trigger button on close
- [ ] First element auto-focuses on open

**Screen Reader:**
- [ ] Modal announced as "dialog" or "menu"
- [ ] Close button has aria-label
- [ ] Backdrop click closes modal (announced)

---

### 3.3 Persona Detail Pages

**Estimated Time:** 3-4 hours
**Priority:** 💎 Nice to Have
**Files Created:** `react-ui/src/pages/PersonaDetail.tsx`
**Impact Score:** ⭐⭐⭐

#### Problem Statement
Users can't view detailed information about a persona before chatting:
- Full lore/backstory
- Expertise areas
- Behavior guidelines
- Example dialogues

#### Solution Design

**Page Structure:**
1. Hero section with large character image
2. Stats card (rarity, style, expertise)
3. Lore/backstory expandable sections
4. Example dialogues showcase
5. "Start Chatting" CTA

#### Implementation Steps

**Step 1: Update Routes**

**File:** `react-ui/src/App.tsx`

```tsx
import PersonaDetail from './pages/PersonaDetail';

<Routes>
  <Route path="/" element={<Home />} />
  <Route path="/characters" element={<CharacterCardV2Showcase />} />
  <Route path="/characters/:personaKey" element={<PersonaDetail />} /> {/* NEW */}
  <Route path="/collection" element={<CharacterCollection />} />
  <Route path="/chat" element={<Chat />} />
  <Route path="/chat/:sessionId" element={<Chat />} />
  <Route path="/stats" element={<Stats />} />
</Routes>
```

**Step 2: Create PersonaDetail Page**

**File:** `react-ui/src/pages/PersonaDetail.tsx` (NEW FILE - 200+ lines)

Due to length, this would include:
- URL parameter extraction (`useParams`)
- Persona data fetching
- Hero section with parallax background
- Expandable lore sections
- Example dialogue carousel
- Related personas suggestions
- "Start Chatting" button that creates session

Implementation details available upon request.

---

## Testing Strategy

### Unit Testing

**Test Coverage Goals:**
- Animation utilities: 90%+
- Stats calculations: 100%
- Search functions: 95%+

**Example Test:**

```typescript
// react-ui/src/utils/__tests__/animations.test.ts
import { ANIMATION_DURATIONS, SPRING_CONFIGS, conditionalAnimation } from '../animations';

describe('Animation System', () => {
  test('ANIMATION_DURATIONS contains expected values', () => {
    expect(ANIMATION_DURATIONS.instant).toBe(0.1);
    expect(ANIMATION_DURATIONS.normal).toBe(0.3);
    expect(ANIMATION_DURATIONS.dramatic).toBe(0.8);
  });

  test('SPRING_CONFIGS have correct structure', () => {
    expect(SPRING_CONFIGS.snappy).toHaveProperty('stiffness', 400);
    expect(SPRING_CONFIGS.smooth).toHaveProperty('damping', 30);
  });

  test('conditionalAnimation respects reduced motion', () => {
    // Mock prefers-reduced-motion
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: jest.fn().mockImplementation(query => ({
        matches: query === '(prefers-reduced-motion: reduce)',
        media: query,
      })),
    });

    const animated = { scale: 1.2 };
    const static = { scale: 1.0 };
    const result = conditionalAnimation(animated, static);

    expect(result).toEqual(static);
  });
});
```

### Integration Testing

**Critical Flows:**
1. Typography loads correctly across all pages
2. Search filters sessions and messages
3. Keyboard navigation works on character cards
4. Focus trap activates in modals

### Accessibility Testing

**Automated:**
- Lighthouse CI (target: 95+ accessibility score)
- axe-core in CI pipeline

**Manual:**
- Keyboard-only navigation test (unplug mouse)
- Screen reader test (NVDA/JAWS/VoiceOver)
- Color contrast checker (WebAIM)
- Reduced motion verification

### Performance Testing

**Metrics:**
- Lighthouse Performance: 90+ score
- First Contentful Paint: <1.5s
- Time to Interactive: <3.5s
- Frame rate: 55+ fps during animations

**Tools:**
- Chrome DevTools Performance tab
- React DevTools Profiler
- Lighthouse CI

---

## Rollout Plan

### Phase 1: Critical (Week 1)

**Day 1-2: Typography**
- Import fonts
- Update all components
- Test across devices

**Day 3-4: Background + Accessibility**
- Implement deep space aesthetic
- Fix keyboard navigation
- Color contrast updates

**Day 5: Testing & Fixes**
- Comprehensive accessibility audit
- Performance profiling
- Bug fixes

### Phase 2: High Impact (Week 2)

**Day 6-7: Search**
- Session search
- Message search
- Testing

**Day 8-9: Buttons + Animations**
- Button hierarchy fixes
- Animation system
- Performance optimization

**Day 10: Integration Testing**
- End-to-end flow testing
- Mobile testing
- Cross-browser checks

### Phase 3: Nice to Have (Week 3+)

**Flexible Timeline:**
- Stats page (2 days)
- Focus trap (1 day)
- Persona details (2 days)
- Polish & refinement (ongoing)

---

## Success Metrics

### Before Implementation (Baseline)
- Overall UX Score: 7.2/10
- Lighthouse Accessibility: ~80
- Lighthouse Performance: ~75
- Keyboard navigation: Broken
- Distinctive visual identity: Low

### After Phase 1 (Critical)
- Overall UX Score: 8.5/10
- Lighthouse Accessibility: 95+
- Distinctive visual identity: High
- Keyboard navigation: Full compliance

### After Phase 2 (High Impact)
- Overall UX Score: 9.0/10
- Lighthouse Performance: 90+
- User engagement: +25% (estimated)
- Search usage: Measurable

### Final Target (All Phases)
- Overall UX Score: 9.5/10
- Lighthouse scores: 95+ all categories
- Zero accessibility violations
- Industry-leading gacha UI

---

## Risk Mitigation

### Risk 1: Font Loading Performance
**Mitigation:**
- Use `font-display: swap` in Google Fonts URL
- Implement fallback fonts
- Consider self-hosting if CDN unreliable

### Risk 2: Animation Performance on Low-End Devices
**Mitigation:**
- Implement performance monitoring
- Reduce particle count on low FPS detection
- Respect `prefers-reduced-motion`

### Risk 3: Search Performance with Large Datasets
**Mitigation:**
- Debounce search input (300ms)
- Virtualize long message lists
- Paginate session list (50 per page)

### Risk 4: Breaking Changes to Existing Features
**Mitigation:**
- Feature flags for gradual rollout
- Comprehensive regression testing
- Git branches for each phase

---

## Maintenance & Future Work

### Immediate Post-Launch
- Monitor analytics for search usage
- Gather user feedback on new typography
- Performance monitoring dashboard

### 3-Month Follow-Up
- Advanced stats (heatmaps, usage patterns)
- A/B test background aesthetics
- Persona detail page expansion

### 6-Month Roadmap
- Animated persona transitions
- Voice input for messages
- Advanced filtering (date ranges, persona groups)
- Export stats as PDF/CSV

---

## Appendix

### A. Color Palette Reference

```css
/* Deep Space Aesthetic */
--bg-space-dark: #0a0e27;
--bg-space-mid: #1a1625;
--bg-space-light: #0f0d1f;

--nebula-blue: rgba(59, 130, 246, 0.12);
--nebula-purple: rgba(139, 92, 246, 0.08);
--nebula-cyan: rgba(34, 211, 238, 0.06);

/* Rarity Colors */
--legendary: #FFD700;
--epic: #DA70D6;
--rare: #00BFFF;
--common: #C0C0C0;

/* Accent Colors */
--accent-primary: #4F46E5; /* Indigo */
--accent-secondary: #EC4899; /* Pink */
```

### B. Typography Scale

```css
--text-xs: 0.75rem;     /* 12px */
--text-sm: 0.875rem;    /* 14px */
--text-base: 1rem;      /* 16px */
--text-lg: 1.125rem;    /* 18px */
--text-xl: 1.25rem;     /* 20px */
--text-2xl: 1.5rem;     /* 24px */
--text-3xl: 1.875rem;   /* 30px */
--text-4xl: 2.25rem;    /* 36px */
--text-5xl: 3rem;       /* 48px */
```

### C. Animation Constants

See `react-ui/src/utils/animations.ts` for full reference.

### D. Accessibility Checklist

**WCAG AA Compliance:**
- [ ] 4.5:1 color contrast for body text
- [ ] 3:1 color contrast for large text
- [ ] Keyboard navigation for all interactive elements
- [ ] Focus indicators (3px outline)
- [ ] Screen reader labels (aria-label, aria-labelledby)
- [ ] Skip links for main content
- [ ] Heading hierarchy (h1 → h2 → h3)
- [ ] Form labels associated with inputs
- [ ] Alternative text for images
- [ ] Reduced motion support

### E. Browser Support

**Tested Browsers:**
- Chrome 100+ (primary)
- Firefox 95+
- Safari 15+
- Edge 100+

**Mobile:**
- iOS Safari 15+
- Chrome Android 100+

**Known Issues:**
- Safari 14 and below: backdrop-filter may not work
- IE11: Not supported (no support planned)

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-26 | UX Assessment | Initial implementation plan |

---

**End of Implementation Plan**
