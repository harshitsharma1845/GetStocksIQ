# 🏛️ SYSTEM ARCHITECTURE DOCUMENT (SAD)
## GetStockIQ — AI-Powered Investment Intelligence & Multi-Factor Market Strategist

* **Document Version:** 1.0 (MVP)
* **Architecture Pattern:** Modular Monolith (Layered MVC + Quantitative Services)
* **Status:** Approved & Production-Ready
* **Author / System Architect:** Harshit Sharma (@harshitsharma1845)
* **PDF Artifact:** [`SAD_STRATIX_AI.pdf`](file:///d:/GetStockIQ/SAD_STRATIX_AI.pdf)

---

## 1. Architecture Overview & 2. Architecture Principles
**GetStockIQ** is engineered as a high-cohesion, low-latency **Modular Monolith** designed for financial equity analysis. The architecture adheres to four core principles:
1. **Deterministic Mathematical Truth:** Quantitative algorithms execute in pure Python before AI synthesis.
2. **Zero-Bloat Frontend:** Server-Side Jinja2 + Vanilla JS ES6+ ensures `<0.5s` page rendering without heavy build steps.
3. **Resilient Fail-Safe Integration:** Multi-tier caching and multi-model LLM fallback cascades prevent external API failures.
4. **Stateless Request Processing:** Session-secured HTTP-only cookies enabling horizontal scaling behind WSGI worker processes.

---

## 3. Technology Stack & 4. Frontend Architecture
* **Backend:** Python 3.13, Flask 3.x, SQLAlchemy ORM, Flask-Login, Flask-Bcrypt, `yfinance`, `requests`.
* **Frontend:** HTML5, Custom CSS3 (Glassmorphism), Vanilla JavaScript (ES6+), Bootstrap Icons, Plotly.js / Chart.js.
* **Client Architecture:** Component-scoped JS modules (`dashboard.js`, `portfolio.js`, `landing-animations.js`) manipulating the DOM asynchronously via `fetch()` APIs.

---

## 5. Backend Architecture & 6. Application Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Layer 1: Presentation                              │
│              HTML5 / CSS3 / Vanilla JS (ES6+) / Jinja2 SSR                  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP / JSON Requests
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Layer 2: Application                               │
│            Flask WSGI Router / CSRF / Auth Guards / Sessions                │
└──────────────────────┬───────────────────────────────┬──────────────────────┘
                       │                               │
         ┌─────────────▼────────────┐    ┌─────────────▼────────────┐
         │ Layer 3: Domain Services │    │ Layer 3: Intelligence    │
         │  StockService / Cache    │    │  ScoringEngine / LLM     │
         │  PortfolioService        │    │  Multi-Model Fallback    │
         └─────────────┬────────────┘    └─────────────┬────────────┘
                       │                               │
                       └───────────────┬───────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Layer 4: Data & External Providers                    │
│            PostgreSQL (SQLAlchemy) • yfinance • OpenRouter LLMs             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Database Architecture & 8. Data Models (ERD)
* `users`: Primary identity model (`id`, `email`, `password`, `risk_profile`, `google_id`).
* `portfolios`: 1-to-many from users; manages portfolio metadata (`id`, `user_id`, `name`, `currency`).
* `holdings`: Active stock positions with unique constraint on `(portfolio_id, symbol)`.
* `transactions`: Immutable trade execution ledger recording `BUY` / `SELL`, quantity, execution price, and fees.
* `watchlist`: Unique `(user_id, symbol)` stock tracking pairs.
* `ai_analysis_cache`: Cached quantitative score records with expiration timestamps.

---

## 9. Market Data Integration & 10. Quantitative Analysis Engine
`StockService` interfaces with `yfinance` using `.NS` / `.BO` ticker symbols. Quotes and 52-week channels are normalized into clean dictionaries. `TechnicalService` computes 14-day RSI, 50/200 DMA alignment, MACD, and Bollinger Bands.

---

## 11. Seven-Factor Scoring Engine & 12. Signal Generation
$$\text{Score} = 0.25\text{Fund} + 0.20\text{Tech} + 0.15\text{Val} + 0.15\text{Mom} + 0.10\text{Sent} + 0.10\text{Risk} + 0.05\text{Liq}$$
* **Signals:** $\ge 80 \to$ **Strong Buy** | $65–79 \to$ **Buy** | $50–64 \to$ **Hold** | $35–49 \to$ **Reduce** | $< 35 \to$ **Avoid**.

---

## 13. Portfolio Diagnostics & 14. Stock Comparison
* **Diagnostics:** Evaluates portfolio risk concentration, beta exposure, and generates actionable rebalancing advice.
* **Comparison:** Fetches parallel metrics for 2+ tickers and calculates head-to-head winner badges for P/E, ROE, and growth.

---

## 15. AI Assistant & 16. OpenRouter Multi-Model Fallback
`VerifiedContextBuilder` constructs immutable prompt contexts containing ground-truth scores. `LLMService` dispatches requests through an ordered model cascade:
`openai/gpt-4o-mini` $\to$ `anthropic/claude-3.5-haiku` $\to$ `google/gemini-2.5-flash` $\to$ `Deterministic Rule Template` with a 12-second timeout per model.

---

## 17. Auth, 18. Authorization, 19. API & 20. Data Flow
* **Authentication:** Flask-Login session management with salted PBKDF2-SHA256 password hashing and Google OAuth 2.0 (GIS).
* **Authorization:** Route protection via `@login_required` and tenant isolation (all queries filter by `current_user.id`).
* **API Flow:** Client sends `fetch()` with `X-CSRF-Token` $\to$ Route Controller $\to$ Service Layer $\to$ Response JSON.

---

## 21. Caching & 22. Storage Strategy
* **Two-Tier Cache:** Fast in-memory dictionary for high-frequency hits + persistent disk cache with TTL eviction.
* **Database Storage:** PostgreSQL with connection pooling (`pool_pre_ping=True`, `pool_size=10`, `max_overflow=20`).

---

## 23. Security, 24. CSRF and Session Security
* **CSRF:** Double-submit session tokens validated on all state-changing HTTP verbs (POST/PUT/DELETE).
* **Headers:** Content Security Policy (CSP), `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`.
* **Cookies:** `HttpOnly=True`, `SameSite='Lax'`, 7-day lifetime.

---

## 25. Error Handling, 26. Logging and Monitoring
* Centralized error handlers for 400, 403, 404, 429, 500.
* Structured Python logging across `investiq.llm`, `investiq.stock`, and `investiq.scoring`.

---

## 27. Deployment Architecture & 28. Environment Configuration
* **WSGI Server:** Gunicorn (4 worker processes) behind an Nginx reverse proxy.
* **Config:** Twelve-factor app configuration managed via `.env` and `config.py`.

---

## 29. Performance, 30. Scalability, 31. Backup & 32. CI/CD
* **Performance:** `< 500ms` First Contentful Paint; persistent caching slashes external API calls by 85%.
* **Scalability:** Stateless app architecture allows horizontal worker scaling on Render / Railway / AWS EC2.
* **Backup & Recovery:** Automated daily snapshots of managed PostgreSQL database.
* **CI/CD:** GitHub Actions workflow executing 9 automated test modules prior to production deployment.

---

## 33. MVP Architecture vs. Future Architecture
* **MVP:** Modular Monolith with Flask SSR, Vanilla JS, yfinance REST polling, and OpenRouter AI.
* **Future Roadmap:** Real-time WebSocket microservices for tick-by-tick order book streaming and direct broker execution gateways.
