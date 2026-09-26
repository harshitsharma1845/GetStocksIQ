# 🎓 GETSTOCKIQ — COMPLETE MENTOR & TECHNICAL PRESENTATION MASTER GUIDE
## AI-Powered Investment Intelligence & Multi-Factor Market Strategist

* **Brand Name:** **GetStockIQ**
* **Project Repository:** [harshitsharma1845/GetStocksIQ](https://github.com/harshitsharma1845/GetStocksIQ)
* **Author / Candidate:** Harshit Sharma (@harshitsharma1845)
* **PDF Artifact:** [`GetStockIQ_Complete_Mentor_MasterGuide.pdf`](file:///d:/GetStockIQ/GetStockIQ_Complete_Mentor_MasterGuide.pdf)

---

## 1. 30-Second Opening Pitch (Speak this to your Mentor)
> *"Sir/Ma'am, I have built **GetStockIQ** — an **AI-Powered Multi-Factor Investment Intelligence & Portfolio Optimization Platform** engineered specifically for Indian equities (NSE/BSE).*
>
> *Retail investors currently suffer from data fragmentation across disparate balance sheets, technical charts, and news portals. GetStockIQ solves this by unifying real-time data ingestion, a deterministic **7-Pillar Quantitative Scoring Engine** (producing Buy, Hold, or Avoid signals), automated portfolio risk health checkups, and a conversational **AI Assistant** wrapped in a modern glassmorphic interface."*

---

## 2. Complete Technology Stack & Architectural Justifications

| Component | Technology | Architectural Rationale (Why You Chose It) |
| :--- | :--- | :--- |
| **Backend Server** | **Python 3.13 + Flask 3.x** | Microsecond WSGI routing overhead, zero async locking, and direct native execution of financial libraries. |
| **Database & ORM** | **Flask-SQLAlchemy (SQLite / PostgreSQL)** | Relational integrity with cascading foreign keys (`User`, `Portfolio`, `Holding`, `Transaction`). SQLite for dev; PostgreSQL in prod. |
| **Market Data API** | **`yfinance` Library (.NS / .BO)** | Fetches live quotes, P/E, EPS, 52-week channels, and historical price trajectories for Indian equities. |
| **Caching Engine** | **Custom 2-Tier Caching (Memory + Disk)** | Prevents external API rate-limiting (HTTP 429) and reduces response latency to `< 500ms`. |
| **AI Gateway** | **OpenRouter Multi-Model Cascade** | Zero-hallucination structured prompt pipeline cascading through GPT-4o-mini $\to$ Claude 3.5 $\to$ Gemini 2.5 $\to$ Offline Rules. |
| **Frontend Core** | **HTML5, CSS3 Glassmorphism, Vanilla JS** | Zero 500MB node_modules bloat; instant `<0.5s` First Contentful Paint and 60fps GPU rendering. |
| **Security & Auth** | **PBKDF2-SHA256, CSRF, 6-digit OTP** | Salted cryptographic password hashing, double-submit CSRF tokens, and expiring OTP password recovery. |

---

## 3. System Architecture & 5 Core Internal Workflows

```
[1. Client Tier] ──► [2. Flask Router] ──► [3. Quant Services] ──► [4. Data & Fallback] ──► [5. AI Synthesis]
  HTML5 / CSS3 / ES6   CSRF / Auth / Sessions   7-Pillar Math / P&L     yfinance / Cache        OpenRouter Gateway
```

* **Flow 1 (Market Data & Caching):** Client queries symbol $\to$ `CacheService` checks memory/disk $\to$ If stale, `StockService` calls `yfinance` $\to$ Stores in cache $\to$ Returns clean JSON.
* **Flow 2 (7-Pillar Quantitative Scoring Engine):** Backend computes weighted composite score:
  $$\text{Score} = 0.25\text{Fund} + 0.20\text{Tech} + 0.15\text{Val} + 0.15\text{Mom} + 0.10\text{Sent} + 0.10\text{Risk} + 0.05\text{Liq}$$
  **Signals:** $\ge 80 \to$ **Strong Buy** | $65–79 \to$ **Buy** | $50–64 \to$ **Hold** | $35–49 \to$ **Reduce** | $< 35 \to$ **Avoid**.
* **Flow 3 (Zero-Hallucination AI Architecture):** Python scoring engine executes first. `VerifiedContextBuilder` packages immutable numbers into read-only prompts. AI acts strictly as an explainer.
* **Flow 4 (Portfolio Math & Trade Execution):** Weighted Avg Buy Price: $\text{Avg Price} = \frac{\sum(\text{Qty}_i \times \text{Price}_i)}{\sum \text{Qty}_i}$. Realized P&L: $(\text{Sell Price} - \text{Avg Buy Price}) \times \text{Sold Qty}$.
* **Flow 5 (Security & Session Auth):** PBKDF2 salted hash verification, HTTP-only session cookies, Google OAuth 2.0 (GIS), and 6-digit OTP resets (10-minute expiry).

---

## 4. Backend Service Architecture (Folder: `services/`)
* `services/stock_service.py`: Market data extraction, ticker normalization (.NS/.BO), day channels, and volume.
* `services/scoring_service.py`: Core 7-pillar mathematical scoring and Buy/Hold/Avoid classification.
* `services/portfolio_service.py`: Trade execution ledger, P&L calculations, and portfolio health diagnostics.
* `services/llm_service.py`: OpenRouter AI Gateway with 4-level model fallback cascade.
* `services/cache_service.py`: Multi-tier memory and persistent disk caching.
* `services/technical_service.py`: RSI (14-day), 50/200 DMA alignments, MACD, and Bollinger Bands.

---

## 5. Database Schema & Entity Relationships

```
┌──────────────────┐       1 : N       ┌──────────────────┐       1 : N       ┌──────────────────┐
│      users       ├──────────────────►│    portfolios    ├──────────────────►│     holdings     │
│ id, email, pass  │                   │ id, user_id, curr│                   │ symbol, qty, avg │
└────────┬─────────┘                   └────────┬─────────┘                   └──────────────────┘
         │                                      │ 1 : N
         │ 1 : N                                ▼
         │                             ┌──────────────────┐
         │                             │   transactions   │
         │                             │ BUY/SELL, amount │
         ▼                             └──────────────────┘
┌──────────────────┐
│    watchlist     │
│  user_id, symbol │
└──────────────────┘
```

---

## 6. Financial Math & Edge Cases
* **Overselling Guard:** If user attempts to sell 15 shares when holding 10, backend rejects with HTTP 400 Bad Request.
* **Negative / Loss-Making P/E:** If earnings are negative, the engine transitions to Price-to-Sales (P/S) and Cash Flow metrics.
* **Partial Share Sales:** Selling partial shares locks in realized P&L while preserving the original Average Buy Price on remaining units.

---

## 7. Step-by-Step Live Demo Script (How to Present)
* **Step 1 (Landing Page):** Scroll to showcase floating pill navbar morphing and animated SVG NIFTY bezier chart curve.
* **Step 2 (Dashboard):** Highlight live portfolio net worth, 24h P&L (+/- pill badge), and market movers.
* **Step 3 (Portfolio & AI Health Check):** Add a trade (Qty 10, Price ₹1500) $\to$ Click 'Run AI Health Check' to demonstrate sector concentration warnings.
* **Step 4 (Compare Stocks):** Select `TCS.NS` and `INFY.NS` $\to$ Demonstrate side-by-side comparison matrix with green winner badges.
* **Step 5 (AI Assistant):** Ask a live financial question to showcase conversational market intelligence.

---

## 8. Top Mentor & Interview Questions with Ready Answers

### **Q1: Why did you choose Flask instead of React + Node.js or Django?**
> **Answer:** *"Flask is a lightweight WSGI micro-framework with microsecond routing latency. Because financial modeling is best done in Python with yfinance, using Flask unifies the entire backend pipeline. Server-rendered Jinja2 templates combined with modern Vanilla JavaScript ES6 eliminate 500MB of node_modules bloat and achieve <0.5s page load speeds."*

### **Q2: What happens if Yahoo Finance API rate-limits or goes offline?**
> **Answer:** *"I implemented a resilient two-tier caching layer (memory + disk). If the external API rate-limits (HTTP 429), the backend seamlessly serves cached recent data and historical baselines, preventing unhandled 500 server errors."*

### **Q3: How do you guarantee the AI will not hallucinate wrong financial numbers?**
> **Answer:** *"Through strict Separation of Concerns. The LLM does not perform calculations. Our Python ScoringEngine computes the exact mathematical scores first. VerifiedContextBuilder passes these numbers into read-only system prompts where the AI is strictly instructed only to explain the verified context."*

### **Q4: How is user security and authentication handled?**
> **Answer:** *"Passwords are hashed using PBKDF2-SHA256 with unique cryptographic salts. Sensitive routes are protected with @login_required, session cookies are configured with HttpOnly=True and SameSite='Lax', and state-changing actions require double-submit CSRF tokens."*

### **Q5: How does the AI Assistant handle API outages with OpenRouter?**
> **Answer:** *"We built a 4-level model fallback cascade (GPT-4o-mini $\to$ Claude 3.5 Haiku $\to$ Gemini 2.5 Flash $\to$ Deterministic Rule Template) with a 12-second timeout per model, guaranteeing zero downtime."*
