# Typing Indicator Layout Fix

**Date:** December 29, 2025
**Status:** ✅ Resolved
**Severity:** Critical UX bug

## Problem

When typing indicators or tool indicators appeared during chat, the entire layout would break:
- Input message bar would jump to the top of the screen
- Huge empty gray space would fill the chat area
- Messages would disappear from view
- Layout only broke when indicators appeared (typing, search, MongoDB tools)

## Root Cause

The typing/tool indicators were absolutely positioned **inside a flex container** as direct siblings to the scrollable messages container. When the `AnimatePresence` wrapper rendered (even though its children were absolutely positioned), it disrupted the flex layout calculation, causing the input bar to misposition.

**Broken Structure:**
```jsx
<div className="flex-1 flex flex-col">  {/* Main Chat Area */}
  <div>Header</div>
  <div className="flex-1 overflow-y-auto">Messages</div>

  {/* THIS WAS THE PROBLEM - flex child affecting layout */}
  <AnimatePresence>
    <div className="absolute bottom-24">Indicator</div>
  </AnimatePresence>

  <div>Input Area</div>
</div>
```

When `AnimatePresence` rendered, the flex container recalculated, pushing the input bar up.

## Solution

**1. Moved indicators inside the Messages Container**
   - Indicators now positioned `fixed` (not `absolute`) relative to viewport
   - No longer part of flex layout calculation
   - `z-index: 50` ensures visibility above all content

**2. Changed positioning from `absolute` to `fixed`**
   - `absolute bottom-24` = positioned relative to scroll container (moves with scroll)
   - `fixed bottom-24` = positioned relative to viewport (stays locked at bottom)

**Fixed Structure:**
```jsx
<div className="flex-1 flex flex-col">  {/* Main Chat Area */}
  <div>Header</div>

  <div className="flex-1 overflow-y-auto relative">  {/* Messages Container */}
    <div>Messages</div>

    {/* Indicators inside Messages Container, fixed to viewport */}
    <AnimatePresence>
      <div className="fixed bottom-24 left-4 z-50 pointer-events-none">
        <TypingIndicator />
      </div>
    </AnimatePresence>
  </div>

  <div>Input Area</div>
</div>
```

## Files Modified

### `react-ui/src/pages/Chat.tsx`

**Lines 437, 466-481:**
```tsx
{/* Messages Container - with indicators positioned absolutely inside */}
<div className="flex-1 overflow-y-auto px-4 md:px-6 py-4 min-h-0 relative">
  <div className="space-y-3 md:space-y-4 pb-20">
    {/* messages */}
  </div>

  {/* Indicators - positioned absolutely inside Messages Container to not affect flex layout */}
  <AnimatePresence mode="wait">
    {isSearching && !initializingSession && toolType !== 'none' && (
      <div className="fixed bottom-24 left-4 md:left-6 z-50 pointer-events-none">
        <ToolIndicator
          toolType={toolType}
          personaName={selectedPersona?.display_name}
          rarity={selectedPersona?.rarity}
        />
      </div>
    )}
    {!isSearching && loading && !initializingSession && (
      <div className="fixed bottom-24 left-4 md:left-6 z-50 pointer-events-none">
        <TypingIndicator />
      </div>
    )}
  </AnimatePresence>
</div>
```

**Key Changes:**
- Added `relative` to Messages Container
- Moved `AnimatePresence` wrapper inside Messages Container
- Changed `absolute` → `fixed` positioning
- Changed `z-10` → `z-50` to ensure visibility
- Added `pointer-events-none` to prevent blocking interactions

### `react-ui/src/components/RichContent.tsx`

**Lines 53-83:** Added `<br>` tag parsing to handle literal HTML breaks from LLM responses.

**Before:**
```tsx
const parseInlineMarkdown = (text: string, startKey: number) => {
  // Process bold first...
  const boldParts: React.ReactNode[] = [];
  text.split(/(\*\*[^*]+\*\*)/).forEach(...)
```

**After:**
```tsx
const parseInlineMarkdown = (text: string, startKey: number) => {
  // Process <br> tags first (literal HTML breaks from LLM)
  const brParts: React.ReactNode[] = [];
  text.split(/(<br\s*\/?>)/i).forEach((segment, i) => {
    if (i % 2 === 0) {
      brParts.push(segment);
    } else {
      brParts.push(<br key={`br-${key++}`} />);
    }
  });

  // Then process bold...
  const boldParts: React.ReactNode[] = [];
  brParts.forEach((part) => {
    if (typeof part === 'string') {
      part.split(/(\*\*[^*]+\*\*)/).forEach(...)
    } else {
      boldParts.push(part);
    }
  });
```

Regex `/(<br\s*\/?>)/i` matches:
- `<br>` (self-closing)
- `<br />` (XHTML style)
- `<BR>` (case-insensitive)

## Testing

Comprehensive tests performed:
- ✅ Initial layout stable (input at bottom, messages scrollable)
- ✅ Typing indicator appears without layout shift
- ✅ Tool indicator appears without layout shift
- ✅ Layout stable after scrolling up in messages
- ✅ Layout stable when sending messages while scrolled up
- ✅ Indicators remain visible regardless of scroll position
- ✅ `<br>` tags render as line breaks (not literal text)

**Test Results:** 8/8 tests passed with Frieren persona
**Screenshots:** `frieren_test_01_initial.png`, `frieren_test_02_typing_indicator.png`, `frieren_test_03_after_response.png`

## Prevention Guidelines

**For future UI development:**

1. **Never add flex children that don't take up space**
   - If a component is absolutely/fixed positioned, place it outside the flex flow
   - Use `fixed` positioning for viewport-locked overlays
   - Use `absolute` positioning only when relative to a specific parent

2. **AnimatePresence positioning**
   - `AnimatePresence` wrappers are still DOM elements in the flex tree
   - Even if children are absolutely positioned, the wrapper affects layout
   - Always place `AnimatePresence` outside flex containers or inside non-flex parents

3. **Indicator positioning pattern**
   ```tsx
   {/* CORRECT - fixed to viewport, outside flex flow */}
   <div className="flex-1 overflow-y-auto relative">
     <div>Content</div>
     <AnimatePresence>
       <div className="fixed bottom-24 z-50">Indicator</div>
     </AnimatePresence>
   </div>

   {/* WRONG - flex child affects layout */}
   <div className="flex flex-col">
     <div className="flex-1">Content</div>
     <AnimatePresence>
       <div className="absolute bottom-24">Indicator</div>
     </AnimatePresence>
     <div>Input</div>
   </div>
   ```

4. **Testing checklist for layout changes**
   - [ ] Send message and verify input bar stays at bottom
   - [ ] Scroll up in messages and send another message
   - [ ] Verify indicators appear without layout shifts
   - [ ] Test with all indicator types (typing, search, tool)
   - [ ] Test with different personas (common, rare, epic, legendary)

## Related Issues

- Initial report: Message bar jumping upward when typing indicator appeared
- Secondary issue: `<br>` tags rendering as literal text instead of line breaks
- Tertiary issue: Indicators invisible after scrolling up in messages

All issues resolved with this fix.

## Deployment

**Docker Rebuild Required:** Yes
**Deployment Date:** December 29, 2025
**Containers Affected:** `ai-companion-web` (frontend)

```bash
cd react-ui && npm run build
docker-compose --env-file .env.docker build frontend
docker-compose --env-file .env.docker up -d frontend
```

## Verification

User-confirmed working after deployment:
- ✅ Layout stable with Frieren persona
- ✅ Typing indicator visible and positioned correctly
- ✅ No layout jumps during message sending
- ✅ `<br>` tags render correctly

---

**Lesson Learned:** Always consider how React component wrappers (`AnimatePresence`, `Fragment`, etc.) participate in layout calculations, even when their children are absolutely positioned. Use `fixed` positioning for viewport-locked overlays, and place them outside flex containers to prevent layout disruption.
