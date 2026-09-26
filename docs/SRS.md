# 📋 SOFTWARE REQUIREMENTS SPECIFICATION (SRS)
## GetStockIQ — AI-Powered Investment Intelligence & Multi-Factor Market Strategist

* **Standard:** IEEE Std 830-1998 Conforming
* **Version:** 1.0 (MVP)
* **Status:** Approved & Production-Ready
* **Author / System Architect:** Harshit Sharma (@harshitsharma1845)
* **PDF Artifact:** [`SRS_STRATIX_AI.pdf`](file:///d:/GetStockIQ/SRS_STRATIX_AI.pdf)

---

## 1. System Overview
**GetStockIQ** is an enterprise-grade full-stack web application designed for quantitative equity research, real-time market data extraction, and automated portfolio optimization. The system ingests Indian equity tickers (NSE/BSE), calculates multi-factor valuations across a 7-Pillar Quantitative Model, and generates deterministic Buy, Hold, or Avoid signals with conversational AI explanations.

---

## 2. User Roles & 3. Role-Based Permissions
* **[ROLE-01] Guest User (Unauthenticated):** Access to public landing page, marketing showcases, and login/register endpoints.
* **[ROLE-02] Authenticated Investor (Registered User):** Access to private dashboard, portfolio ledger, trade actions, stock comparison, watchlist management, and AI health checkups.
* **[ROLE-03] Background Service / Worker:** Automated TTL cache eviction, fallback model cascade, and external API error mitigation.

---

## 4. Functional Requirements Overview
Spans 8 core modules: Authentication, Dashboard, Portfolio Management, Market Discovery, Multi-Factor Scoring, Stock Comparison, Conversational AI Assistant, and User Profile.

---

## 5. Authentication & 6. Authorization Requirements
* **[REQ-AUTH-001] [MANDATORY]:** Passwords SHALL be hashed using PBKDF2 with SHA-256 and unique per-user cryptographic salts.
* **[REQ-AUTH-002] [MANDATORY]:** Google OAuth 2.0 (Google Identity Services) SHALL verify JWT ID tokens on the backend before session issuance.
* **[REQ-AUTH-003] [MANDATORY]:** The system SHALL support 6-digit OTP password reset expiring within 600 seconds (10 minutes).
* **[REQ-AUTH-004] [MANDATORY]:** `@login_required` guards SHALL protect all private routes (`/dashboard`, `/portfolio`, `/watchlist`, `/compare`, `/analysis`, `/profile`).

---

## 7. Portfolio Management Requirements
* **[REQ-PORT-001] [MANDATORY]:** Support recording BUY and SELL transactions with input bounds ($1 \le \text{Qty} \le 1,000,000$ and $₹0.01 \le \text{Price} \le ₹10,000,000$).
* **[REQ-PORT-002] [MANDATORY]:** On accumulating holdings, compute weighted average buy price: $\text{Avg Price} = \frac{\sum(\text{Qty}_i \times \text{Price}_i)}{\sum \text{Qty}_i}$.
* **[REQ-PORT-003] [MANDATORY]:** Calculate total invested value, current market valuation, total unrealized P&L, and realized P&L across all active holdings.
* **[REQ-PORT-004] [MANDATORY]:** Support 1-click portfolio CSV data export.

---

## 8. Market Data & 9. Seven-Pillar Quantitative Scoring Requirements
* **[REQ-DATA-001] [MANDATORY]:** Ingest live stock quotes and technical indicators from `yfinance` using `.NS` / `.BO` suffixes.
* **[REQ-SCOR-001] [MANDATORY]:** Compute composite stock ratings ($0–100$) strictly according to the deterministic weighted formula:
  $$\text{Composite} = 0.25\text{Fund} + 0.20\text{Tech} + 0.15\text{Val} + 0.15\text{Mom} + 0.10\text{Sent} + 0.10\text{Risk} + 0.05\text{Liq}$$

---

## 10. Buy / Hold / Avoid Signal Requirements
* **[REQ-SIGN-001] [MANDATORY]:** Score $\ge 80 \to$ **Strong Buy** | $65–79 \to$ **Buy** | $50–64 \to$ **Hold** | $35–49 \to$ **Reduce** | $< 35 \to$ **Avoid**.
* **[REQ-SIGN-002] [MANDATORY]:** Signal classification SHALL be 100% deterministic and immutable by external prompt injections.

---

## 11. Portfolio Diagnostics & 12. Stock Comparison Requirements
* **[REQ-DIAG-001] [MANDATORY]:** Flag any single sector exceeding 40% of total portfolio value during AI diagnostics.
* **[REQ-COMP-001] [MANDATORY]:** Comparison matrix SHALL evaluate multiple tickers side-by-side across Market Cap, P/E, ROE, 1-Year Returns, and Composite Ratings with winner highlight badges.

---

## 13. AI Assistant & 14. OpenRouter Model Fallback Requirements
* **[REQ-LLM-001] [MANDATORY]:** The AI Assistant (`/api/ask-ai`) SHALL ingest verified numerical context from `VerifiedContextBuilder` and never hallucinate unsupplied numbers.
* **[REQ-LLM-002] [MANDATORY]:** Enforce an ordered multi-model fallback cascade (`openai/gpt-4o-mini` $\to$ `claude-3.5-haiku` $\to$ `gemini-2.5-flash` $\to$ Rule Template) with a 12-second timeout per model.

---

## 15. Data & 16. Database Requirements
* **[REQ-DB-001] [MANDATORY]:** Schema SHALL maintain relational tables: `users`, `portfolios`, `holdings`, `transactions`, `watchlist`, `portfolio_snapshots`, `stock_alerts`, and `ai_analysis_cache`.
* **[REQ-DB-002] [MANDATORY]:** User deletion SHALL trigger cascading deletion (`cascade='all, delete-orphan'`) on associated portfolios, watchlists, and transactions.

---

## 17. API & 18. Input Validation Requirements
* **[REQ-VAL-001] [MANDATORY]:** Stock symbols SHALL strictly match regex `^[A-Za-z0-9._^+-]{1,20}$`.
* **[REQ-VAL-002] [MANDATORY]:** All JSON state-changing requests SHALL require double-submit CSRF token validation.

---

## 19. Business Rules & 20. Error Handling
* **[REQ-BUS-001] [MANDATORY]:** Selling more shares than currently held in the portfolio SHALL be rejected with HTTP 400 Bad Request.
* **[REQ-ERR-001] [MANDATORY]:** On external API failure, return cached metrics without raising an unhandled 500 exception.

---

## 21. Edge Cases & 22. Security Requirements
* **[REQ-SEC-001] [MANDATORY]:** Session cookies SHALL be configured with `HttpOnly=True`, `SameSite='Lax'`, and 16MB maximum payload limits.
* **[REQ-SEC-002] [MANDATORY]:** Attach Content Security Policy (CSP), `X-Content-Type-Options: nosniff`, and `X-Frame-Options: SAMEORIGIN` to all HTTP responses.

---

## 23. Privacy, 24. Performance & 25. Availability
* **[REQ-PERF-001] [MANDATORY]:** Landing page First Contentful Paint (FCP) SHALL be `< 500ms`; REST API latency SHALL be `< 800ms` for cached hits.
* **[REQ-AVAL-001] [MANDATORY]:** Achieve 99.9% uptime with connection pooling (`pool_pre_ping=True`, `pool_size=10`).

---

## 26. Logging, 27. Responsive & 28. Integration
* **[REQ-RESP-001] [MANDATORY]:** UI SHALL render adaptively across viewport widths from 320px (mobile) to 2560px (4K desktop) with minimum 44px touch targets.
* **[REQ-INTG-001] [MANDATORY]:** External integration gateways SHALL operate with strict request timeouts (5s to 12s).

---

## 29. System Acceptance Criteria
1. All 13 application routes return HTTP 200 during automated test execution.
2. Composite score calculation passes 100% of boundary test cases in `tests/test_scoring.py`.
3. LLM gateway fallback cascade triggers correctly under simulated API failures in `tests/test_llm_fallback_system.py`.
4. CSRF protection successfully blocks unauthorized requests in `tests/test_security_hardening.py`.
