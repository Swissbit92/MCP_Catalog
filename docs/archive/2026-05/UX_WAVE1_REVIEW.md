---
title: UX Wave 1 Review — 2026-02-18
status: completed
created: 2026-04-03
last_reviewed_on: 2026-04-19
review_in: 24 months
applies_to: nephilim
---

# UX Wave 1 Review — 2026-02-18

## Status: PARTIAL PASS → FIXED

The UX gatekeeper reviewed during the frontend agent's write window. Three of four files
appeared absent at review time but were completed shortly after. All confirmed issues
have been patched immediately after review.

---

## File Status at Review vs. Final

| File | At Review | Final |
|------|-----------|-------|
| `TradeProposalCard.tsx` | Present, had issues | Present, **fixed** |
| `StrategyApprovalCard.tsx` | Not yet written | Present ✅ |
| `MessageBubble.tsx` wallet detection | Not yet written | Present ✅ |
| `api.ts` wallet functions | Not yet written | Present ✅ |

---

## TradeProposalCard Review

File: `react-ui/src/components/TradeProposalCard.tsx`

### Visual Design — PASS (after fix)

**Fixed:** Background changed from `bg-black/40` → `bg-white/[0.05]` (correct NEPHILIM
glassmorphism recipe). The card now visually matches the void aesthetic.

**Token amount/symbol hierarchy — PASS.** `from_token` in `text-yellow-400/80` (Archon
brand), `to_token` in `text-green-400/80`. Amounts in `font-bold text-xl`. Hierarchy correct.

**Confirm/Cancel button colors — PASS.** Green confirm, subtle cancel. No ambiguity.

### Accessibility — PASS (after fixes)

**Fixed:** All `text-white/40` → `text-white/60` (lines 94, 105, 132).
All `text-white/50` → `text-white/60` (lines 88, 101, 107, 115).

**Fixed:** `focus:ring-2 focus:ring-green-400/50` added to Confirm button.
`focus:ring-2 focus:ring-white/20` added to Cancel button.

**HTML entity rendering — PASS (was already correct).** Line 148 uses JSX
`<><span aria-hidden="true">&#10003;</span> Confirm Trade</>` — entities render
correctly in JSX context. UX gatekeeper reviewed a pre-final version.

**Color + text labels — PASS.** All states (confirmed/cancelled/expired) have both
color AND text label.

### UX Flow — PASS (after fix)

**Fixed:** Timer urgency escalation added. `timerColor` variable:
- `< 30s` → `text-red-400`
- `< 60s` → `text-orange-400`
- Otherwise → `text-white/60`

Timer auto-expires and removes action buttons ✅. Loading state ✅. Inline error ✅.

### NEPHILIM Aesthetic — PASS

Glassmorphism: ✅ (fixed). Archon gold header: ✅. Outfit font for header: ✅.
Manrope body: ✅. Framer Motion entrance: ✅.

---

## StrategyApprovalCard Review

File: `react-ui/src/components/StrategyApprovalCard.tsx`

Written by frontend agent after UX review window. Should be reviewed in Wave 2 QA pass.
Expected to match the same design system rules.

**To verify in Wave 2:**
- Background uses `bg-white/[0.05]` not `bg-black/N`
- No `text-white/40` or `text-white/50`
- Risk warning present before Approve button
- `focus:ring` on action buttons
- Expandable parameters section functional

---

## MessageBubble Integration — PASS

File: `react-ui/src/components/MessageBubble.tsx`

Detection confirmed present (grepped after frontend agent completed):
- Line 8–9: imports `TradeProposalCard` and `StrategyApprovalCard`
- Line 154: checks `proposalType === 'trade_proposal'`
- Line 168: checks `proposalType === 'strategy_proposal'`
- Cards render below text content (not replacing it)

---

## API Functions — PASS

File: `react-ui/src/services/api.ts`

All required functions present (grepped after frontend agent completed):
- `confirmTrade()` at line 616
- `cancelTrade()` at line 628
- `approveStrategy()` at line 640
- `WalletBalance` interface at line 610
- `getWalletBalance()` at line 694

---

## Issues Resolved

| # | Issue | Severity | Resolution |
|---|-------|----------|-----------|
| 1 | `bg-black/40` not glassmorphism | Medium | Fixed → `bg-white/[0.05]` |
| 2 | `text-white/40` WCAG violation (×2) | High | Fixed → `text-white/60` |
| 3 | `text-white/50` below minimum (×4) | Medium | Fixed → `text-white/60` |
| 4 | No `focus:ring` on buttons | Medium | Fixed — added to both |
| 5 | No timer urgency escalation | Low | Fixed — red/orange at <30s/<60s |
| 6 | HTML entity in JS string | High | Not present in final code — pre-patch concern |

---

## Remaining Action Items for Wave 2

- [ ] Review `StrategyApprovalCard.tsx` for same WCAG/glassmorphism issues
- [ ] Verify `ResponseMetadata` type discriminant in `api.ts` for safe MessageBubble detection
- [ ] Add exit animations to both cards (post-action state transitions)

---

## Overall UX Verdict

**APPROVED for Wave 2** (subject to `StrategyApprovalCard` spot-check on WCAG compliance).
All high-priority issues in `TradeProposalCard.tsx` have been resolved. The three
initially missing files are now present and integrated. The rendering pipeline from
chat message → proposal detection → card display → API confirmation is complete.
