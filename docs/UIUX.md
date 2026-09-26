# 🎨 UI/UX DESIGN & COMPONENT SPECIFICATION
## GetStockIQ — AI-Powered Investment Intelligence & Multi-Factor Market Strategist

* **Document Version:** 1.0 (MVP)
* **Design Theme:** High-Contrast Institutional Glassmorphism
* **Status:** Approved & Implementation Ready
* **Author / UI/UX Architect:** Harshit Sharma (@harshitsharma1845)
* **PDF Artifact:** [`UIUX_STRATIX_AI.pdf`](file:///d:/GetStockIQ/UIUX_STRATIX_AI.pdf)

---

## 1. UX Goals & 2. Design Principles
The primary UX goal of **GetStockIQ** is to eliminate financial cognitive fatigue. The design adheres to three core principles:
1. **Clarity Over Decoration:** High-contrast metrics, legible typography, instant Buy/Hold/Avoid badges.
2. **Sub-Second Tactile Feedback:** Smooth button hover/active states, modal transitions, and non-blocking loading skeletons.
3. **Spatial Cohesion:** Unified glassmorphic depth hierarchy across desktop and mobile devices.

---

## 3. Visual Direction, 4. Color / Typography & 5. Glassmorphism System
* **Color Palette:** Brand Royal Purple (`#7c3aed`, `#5b21b6`), Slate Dark Neutral (`#0f172a`), Emerald Success (`#16a34a`), Crimson Danger (`#ef4444`), Amber Warning (`#f59e0b`).
* **Typography:** System Font Stack (`Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`) with strict optical sizing.
* **Glassmorphism Standards:** Background `rgba(255, 255, 255, 0.75)` (Light) / `rgba(30, 27, 75, 0.6)` (Dark) with `backdrop-filter: blur(16px)` and `border: 1px solid rgba(255, 255, 255, 0.15)`.

---

## 6. Responsive Rules, 7. Personas & 8. Primary User Journey
`Landing Page` $\to$ `Login / OTP` $\to$ `Executive Dashboard` $\to$ `Watchlist / Market` $\to$ `Stock Analysis` $\to$ `Compare Matrix` $\to$ `Portfolio AI Diagnostics`.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          1. GLOBAL HEADER & SEARCH                          │
│               Brand Logo • Search Autocomplete • User Profile Avatar        │
├─────────────────────────────────────────────────────────────────────────────┤
│                          2. EXECUTIVE METRIC CARDS                          │
│        Net Worth (₹) • 24h P&L (+/- %) • Health Gauge • Cash Reserves       │
├─────────────────────────────────────────────────────────────────────────────┤
│                          3. VISUAL INSIGHTS GRID                            │
│           7-Pillar Quantitative Scores • Multi-Asset Donut Chart            │
├─────────────────────────────────────────────────────────────────────────────┤
│                          4. INTERACTIVE ACTION LEDGER                       │
│           Holdings Table • Head-to-Head Compare • AI Assistant Chat         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Information Architecture & 10. Navigation Structure
* **Desktop Nav:** Sticky glassmorphic top navbar with search autocomplete, navigation links (Dashboard, Portfolio, Market, Compare, Watchlist), and user profile avatar dropdown.
* **Mobile Nav:** Fixed bottom tab bar (44px+ touch targets) with quick-access drawers for trades and watchlist items.

---

## 11. Authentication Screens & 12. Onboarding Flow
Centered frosted glass authentication card with Google GIS OAuth 2.0 button, email/password inputs, inline validation errors, and 6-digit OTP verification view.

---

## 13. Executive Dashboard & 14. Net Worth Tracker
* **Top Metric Cards:** Total Portfolio Value (large prominent currency format), Total Invested, 24h P&L (+/- pill badge), and Cash Reserves.
* **Asset Donut / Allocation Bar:** Visual multi-asset progress tracks (Equities 65%, Debt/Gold 25%, Cash 10%).

---

## 15. Portfolio View & 16. Portfolio Diagnostics Screen
* **Holdings Ledger:** Table view with ticker symbol, quantity, avg price, current price, unrealized P&L%, and 1-tap trade modal.
* **AI Health Check Modal:** Glassmorphic overlay displaying 0–100 health gauge, sector concentration warnings, and actionable rebalancing bullet points.

---

## 17. Stock Research, 18. Seven-Pillar Analysis & 19. Signal UI
* **7-Pillar Cards:** Fundamentals (25%), Technicals (20%), Valuation (15%), Momentum (15%), Sentiment (10%), Risk (10%), Liquidity (5%).
* **Signal Badges:** **Strong Buy** (Emerald Solid), **Buy** (Green Outline), **Hold** (Amber), **Reduce** (Orange), **Avoid** (Crimson).

---

## 20. Stock Comparison Matrix & 21. AI Assistant Chat UI
* **Compare Matrix:** Side-by-side comparative table with winner highlight badges comparing P/E, ROE, 1Y Return, and Composite Score.
* **AI Chat Drawer:** Collapsible right-side conversational assistant with markdown formatting, syntax highlighting, and instant query chips.

---

## 22. Profile, 23. Settings & 24. Reusable UI Components
Metric Badges, Glass Cards, Modal Dialogs, Search Autocomplete Dropdowns, Toast Notifications, and Action Buttons.

---

## 25. Forms, Validation States (26. Loading, 27. Empty, 28. Error, 29. Success)
* **Loading:** CSS skeleton pulse animations (`.skeleton-loader`) and spinner overlays during network requests.
* **Empty States:** Illustrated placeholder containers with clear Call-to-Action buttons.
* **Error & Success:** Floating toast banners auto-dismissing after 4000ms with manual close triggers.

---

## 30. Dialogs, 31. Tooltips, 32. Micro-Interactions & 33. SVG Animations
* **SVG Draw Animations:** Native `stroke-dasharray` transitions triggered via `IntersectionObserver` on viewport entry.
* **3D Card Hover:** Subtle GPU-accelerated mouse tilt physics (`perspective(1000px) rotateX(...) rotateY(...)`).

---

## 34. Mobile / Tablet / Desktop UX & 37. Accessibility (WCAG 2.1 AA)
* **Accessibility:** Minimum 4.5:1 color contrast ratio for text, full keyboard focus rings (`:focus-visible`), and semantic ARIA labels.
* **Breakpoints:** Mobile ($\le 620\text{px}$), Tablet ($\le 980\text{px}$), Desktop ($> 980\text{px}$), Wide Desktop ($\ge 1440\text{px}$).

---

## 39. Component Interaction Rules & 40. UX Acceptance Criteria
1. All interactive targets meet the minimum 44px $\times$ 44px tap area requirement.
2. Modals trap focus and close cleanly upon pressing `Escape` or clicking outside the backdrop.
3. Chart curves and number counters animate smoothly at 60fps without layout shifts (CLS $< 0.1$).
4. Responsive views adapt flawlessly across 320px to 2560px screen dimensions.
