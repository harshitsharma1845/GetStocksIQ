# 📄 PRODUCT REQUIREMENT DOCUMENT (PRD)
## GetStockIQ — AI-Powered Investment Intelligence & Multi-Factor Market Strategist

* **Document Version:** 1.0 (MVP)
* **Status:** Approved & Implementation Ready
* **Document Format:** Standard A4 Professional Specification
* **Author / Maintainer:** Harshit Sharma (@harshitsharma1845)

---

## 1. Problem Statement
Retail and independent equity investors in Indian stock markets (NSE/BSE) face severe **information fragmentation** and **analytical friction**:
* Financial data is scattered across disconnected tools: fundamental metrics on annual reports, technical momentum on charting terminals, and manual spreadsheets for portfolio tracking.
* Investors suffer from cognitive overload, lack automated tools to detect uncompensated risk concentrations, and have no deterministic methodology to generate structured **Buy, Hold, or Avoid** investment decisions.

---

## 2. Product Vision
To build an institutional-grade, zero-clutter equity research and portfolio optimization web application that unifies real-time market data, a deterministic **7-Pillar Quantitative Scoring Engine**, and structured conversational AI intelligence into an intuitive, high-performance interface.

---

## 3. Target Users
1. **Retail Equity Investors:** Seeking objective, math-backed stock ratings without Wall Street jargon.
2. **Active Traders & Swing Investors:** Requiring technical momentum indicators, RSI setups, and risk-reward bands.
3. **Long-Term Portfolio Managers:** Needing automated asset allocation audits, sector concentration alerts, and rebalancing recommendations.

---

## 4. User Personas

### Persona A: Aarav (28, Software Engineer & Self-Directed Investor)
* **Context:** Has ₹10L invested across 15 stocks.
* **Pain Point:** Spends 4+ hours every weekend manually checking balance sheets and news.
* **Need:** A 1-click diagnostic tool to audit portfolio health and identify over-concentrated tech holdings without analyzing 15 balance sheets manually.

### Persona B: Priya (35, Conservative Wealth Builder)
* **Context:** Values steady capital compounding and capital preservation.
* **Pain Point:** Overwhelmed by conflicting financial news and subjective analyst opinions.
* **Need:** Head-to-head stock comparisons (e.g. TCS vs. Infosys) and clear risk scores (1–100) before making long-term capital allocation decisions.

---

## 5. Product Goals
* **Deterministic Decision Making:** Eliminate subjective bias by calculating transparent, weighted composite scores across 7 quantitative pillars.
* **Sub-Second Responsiveness:** Ensure initial page loads render in `< 0.5s` via server-side rendering and lightweight Vanilla JS.
* **Zero-Hallucination AI Architecture:** Enforce strict separation between quantitative math (backend ground truth) and natural language generation (AI synthesis).

---

## 6. Non-Goals (Out of Scope for MVP)
* Direct broker order execution or algorithmic automated trading via broker APIs (simulated ledger only).
* Intraday microsecond tick-by-tick websocket streaming (quote polling / page refresh used).
* High-frequency algorithmic backtesting environments.

---

## 7. Core Features & 7-Pillar Scoring Architecture

The platform evaluates every stock ticker through a deterministic weighted quantitative model:

| Pillar | Weight | Key Metrics Evaluated |
| :--- | :---: | :--- |
| **Fundamentals** | **25%** | ROE, ROCE, Profit Margin, Debt-to-Equity, Solvency, Cash Flow |
| **Technicals** | **20%** | Moving Averages (50 DMA / 200 DMA), RSI (14-day), MACD, Bollinger Bands |
| **Valuation** | **15%** | P/E Ratio, Forward P/E, PEG Ratio, P/B Ratio, EV/EBITDA, Dividend Yield |
| **Momentum** | **15%** | Multi-timeframe Returns (1M, 3M, 6M, 1Y), 52-Week Range Position |
| **Sentiment** | **10%** | News Sentiment Analysis and Headline Tone Scoring |
| **Risk Resilience** | **10%** | Volatility (Beta), Max Drawdown, Value at Risk (VaR), Leverage |
| **Liquidity** | **5%** | Daily Rupee Turnover, Free-Float Market Capitalization |

**Signal Classification:**
* Composite Score $\ge 80 \to$ **Strong Buy**
* Composite Score $65 - 79 \to$ **Buy**
* Composite Score $50 - 64 \to$ **Hold**
* Composite Score $35 - 49 \to$ **Reduce**
* Composite Score $< 35 \to$ **Avoid**

---

## 8. Technical Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          1. FRONTEND TIER (Client)                          │
│     HTML5 • Modern CSS3 (Glassmorphism) • Vanilla JS (ES6+) • SVG Charts    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP / JSON Requests
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       2. BACKEND CONTROLLER (Server)                        │
│    Python 3.13 + Flask 3.x • WSGI Router • Secure Sessions (PBKDF2 / OTP)   │
└──────────────────────┬───────────────────────────────┬──────────────────────┘
                       │                               │
         ┌─────────────▼────────────┐    ┌─────────────▼────────────┐
         │  3. FINANCIAL ENGINE     │    │  4. AI DIAGNOSTICS       │
         │   yfinance API + Cache   │    │   Multi-Factor Scoring   │
         │   NSE / BSE Real-time    │    │   Risk Profile Matching  │
         └─────────────┬────────────┘    └─────────────┬────────────┘
                       │                               │
                       └───────────────┬───────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          5. DATA & STATE STORE                              │
│         User Profiles • Portfolios • Watchlists • OTP Token Store           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. MVP Scope

1. **Landing Page:** Floating pill navbar, interactive SVG benchmark charts, and marketing funnels.
2. **Auth & Security:** PBKDF2 password hashing, Google Sign-In, 6-digit OTP reset, and CSRF protection.
3. **Dashboard:** Portfolio valuation, net worth tracking, daily P&L, and market gainers/losers.
4. **Portfolio Manager:** Holdings ledger, Buy/Sell trade logging, realized/unrealized P&L, and CSV export.
5. **AI Health Check:** Automated portfolio risk checkup and sector diversification scoring.
6. **Stock Analysis:** In-depth 7-pillar radar ratings, valuation multiples, and technical momentum.
7. **Compare Engine:** Side-by-side comparative analysis of competing Indian equities.
8. **Conversational AI Assistant (`/api/ask-ai`):** Context-aware market intelligence chatbot.

---

## 10. User Stories

* **US-01 (Stock Screening):** As an investor, I want to view a single composite score (0–100) for a stock so that I can immediately determine if it is a Buy, Hold, or Avoid.
* **US-02 (Portfolio Health):** As a portfolio owner, I want to click 'Run AI Health Check' to audit sector over-concentration and receive actionable rebalancing recommendations.
* **US-03 (Stock Comparison):** As an analyst, I want to compare TCS and Infosys side-by-side to determine which company possesses superior valuation and return on equity.
* **US-04 (Account Security):** As a user, I want to reset my password using a 6-digit OTP sent to my email so that my account remains secure.

---

## 11. End-to-End User Journey

```
[Landing Page] ──► [Register / Login] ──► [Dashboard] ──► [Watchlist & Market] ──► [Compare & Analysis] ──► [AI Health Check]
```

---

## 12. Functional Scope & API Route Specification

| Route | Method | Auth | Functional Responsibility |
| :--- | :---: | :---: | :--- |
| `/` | `GET` | No | Marketing landing page with interactive SVG charts. |
| `/login`, `/register` | `GET/POST` | No | User authentication and credential hashing via PBKDF2. |
| `/forgot-password` | `GET/POST` | No | 6-digit OTP generation and password reset flow. |
| `/dashboard` | `GET` | Yes | Executive dashboard displaying net worth and market feed. |
| `/portfolio` | `GET` | Yes | Holdings ledger, asset allocation, and trade actions. |
| `/watchlist` | `GET` | Yes | User-customized stock tracker with real-time quotes. |
| `/compare-results` | `GET` | Yes | Side-by-side comparative financial matrix. |
| `/analysis` | `GET` | Yes | 7-pillar quantitative evaluation and valuation multiples. |
| `/api/ask-ai` | `POST` | Yes | Natural language AI financial assistance endpoint. |
| `/api/portfolio/ai-analysis`| `POST` | Yes | Portfolio health diagnostic and risk rebalancing engine. |

---

## 13. Success Metrics & Key Performance Indicators (KPIs)

* **Performance:** First Contentful Paint (FCP) `< 0.5s`; 99th percentile API response time `< 800ms`.
* **Reliability:** 99.9% uptime with 0% catastrophic downtime during external API rate-limiting via resilient cache fallbacks.
* **Accuracy:** 100% deterministic consistency between quantitative score math and AI verbal synthesis.

---

## 14. Assumptions

* Market data provider (`yfinance`) provides accessible financial history for primary NSE/BSE listed tickers.
* Target users operate modern web browsers supporting ES6 JavaScript and CSS `backdrop-filter`.

---

## 15. Dependencies

* **Backend:** Python 3.13, Flask 3.x, SQLAlchemy, Flask-Login, Flask-Bcrypt, `yfinance`, `requests`.
* **External Gateway:** OpenRouter API / Groq API (LLM inference) and Google Identity Services (OAuth 2.0).

---

## 16. Risks and Mitigations

* **Risk 1 (External API Throttling):** `yfinance` rate-limiting. $\to$ **Mitigation:** Integrated persistent two-tier cache with TTL expiration.
* **Risk 2 (LLM Hallucination):** AI inventing inaccurate stock prices. $\to$ **Mitigation:** `VerifiedContextBuilder` feeds immutable numerical ground-truth into system prompts.
* **Risk 3 (CSRF / Session Hijacking):** Unauthorized state changes. $\to$ **Mitigation:** Strict double-submit CSRF tokens and `HttpOnly`/`SameSite` session cookies.

---

## 17. MVP Acceptance Criteria

1. All 13 core web routes return HTTP 200 without unhandled exceptions.
2. 7-pillar composite scoring generates deterministic ratings for any valid Indian ticker (`.NS` / `.BO`).
3. Portfolio P&L and asset allocation recalculate accurately upon executing Buy/Sell transactions.
4. 6-digit OTP password recovery flow successfully validates and updates user credentials.

---

## 18. Future Enhancements (Post-MVP Roadmap)

* **Phase 2:** Direct broker integration (Zerodha Kite / Upstox API) for 1-click real order execution.
* **Phase 3:** WebSocket-based real-time intraday tick streaming and automated Telegram/WhatsApp rebalance alerts.
* **Phase 4:** Machine learning quantitative price forecasting (LSTM / Prophet time-series models).
