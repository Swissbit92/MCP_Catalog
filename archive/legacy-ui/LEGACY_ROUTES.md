# Legacy Routes — Archived from Phase 7A

These routes were removed from `App.tsx` during the Phase 7 NEPHILIM UI transition.

## Removed Routes

| Route | Component | Purpose |
|-------|-----------|---------|
| `/` | `Home` | Legacy landing page with gacha/browse CTAs |
| `/cards-v2` | `CharacterCardV2Showcase` | Alias for `/select` |
| `/collection` | `CharacterCollection` | Standalone collection view |

## Route Mapping (Legacy → NEPHILIM)

| Legacy Route | New Route | Notes |
|-------------|-----------|-------|
| `/` | `/` | Now serves NephilimHome instead of Home |
| `/nephilim` | `/` | NEPHILIM portal is now the root |
| `/nephilim/onboarding` | `/onboarding` | Simplified path |
| `/cards-v2` | `/select` | Canonical path only |
| `/collection` | `/select` (Bonds Forged tab) | Integrated into showcase page |

## Rollback Instructions

To restore legacy routing:
1. Copy `archive/legacy-ui/pages/Home.tsx` back to `react-ui/src/pages/Home.tsx`
2. Re-add legacy routes to `App.tsx`:
   ```tsx
   <Route path="/" element={<Home />} />
   <Route path="/cards-v2" element={<CharacterCardV2Showcase />} />
   <Route path="/collection" element={<CharacterCollection ... />} />
   ```
3. Move NEPHILIM routes back under `/nephilim` prefix
4. Restore conditional `nephilim-mode` body class logic
5. No backend changes required
