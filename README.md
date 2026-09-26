# 📈 GetStockIQ — AI-Powered Investment Intelligence & Multi-Factor Market Strategist

> **Smarter Market Intelligence. Superior Portfolio Alpha.**  
> Transform raw market data into high-conviction decisions with a 7-pillar quantitative scoring engine, automated portfolio health diagnostics, and real-time AI intelligence for Indian equities (NSE/BSE).

---

## 🌟 Overview

**GetStockIQ** is an institutional-grade, web-based financial research and portfolio management platform engineered to solve financial data fragmentation for retail and professional investors.

The platform unifies real-time market data ingestion, a **7-Pillar Quantitative Scoring Engine**, automated portfolio risk diagnostics, and conversational AI assistance into an intuitive, high-performance glassmorphic user interface.

---

## 📚 Complete Project Documentation Suite

All detailed engineering, design, and architecture specifications are available in the [docs/](docs/) directory:

| Document | Description | Format |
| :--- | :--- | :---: |
| 📄 **[PRD — Product Requirements Document](docs/PRD.md)** | Core problems, user personas, KPI metrics, 7-pillar model scope | Markdown |
| 📄 **[SRS — Software Requirements Specification](docs/SRS.md)** | IEEE 830 standard specifications, functional & non-functional requirements | Markdown |
| 📄 **[SAD — System Architecture Document](docs/SAD.md)** | Modular monolith design, 4-tier layer model, database ERD, caching strategy | Markdown |
| 📄 **[UI/UX — Design & Component Specification](docs/UIUX.md)** | Glassmorphism design system, SVG bezier animations, responsive rules | Markdown |
| 📄 **[DEVPLAN — Master Development Plan](docs/DEVPLAN.md)** | Engineering roadmap, agile milestones (M1–M9), release criteria | Markdown |
| 📄 **[PRESENTATION_GUIDE — Team Presentation & Viva Guide](docs/PRESENTATION_GUIDE.md)** | Bilingual speaking scripts (Hinglish + English), live demo flows, viva Q&As | Markdown |
| 📄 **[COMPLETE_DOCUMENTATION — Technical Deep-Dive](docs/COMPLETE_DOCUMENTATION.md)** | Comprehensive 140-point technical architecture & mathematical breakdown | Markdown |

---

## 🏛️ System Architecture

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

### 🎨 Frontend Architecture
- **Framework & Templating**: **Flask + Jinja2** server-rendered templates (SSR).
- **Styling & Design System**: Modern **CSS3 Glassmorphism** (`backdrop-filter: blur(16px)`), CSS variables, Royal Purple theme.
- **Client-Side Scripting**: **Vanilla ES6+ JavaScript** (zero heavy bundler lock-in, instant `<0.5s` load times).
- **Interactive Visualizations**: GPU-accelerated SVG bezier path draw animations, **Chart.js** & **Plotly.js** for historical price series.

### ⚙️ Backend Architecture
- **Language & Runtime**: **Python 3.12+ / 3.13**
- **Web Framework**: **Flask 3.x** microframework (WSGI)
- **ORM & Data Layer**: **Flask-SQLAlchemy**
- **Authentication & Security**: **Flask-Login** (Session isolation), **Flask-Bcrypt** & **Werkzeug** (Salted PBKDF2-SHA256), Google Identity Services (GIS OAuth 2.0), Double-Submit CSRF tokens.
- **Caching & Rate-Limit Protection**: Resilient 2-tier memory and persistent disk caching with TTL eviction.

### 🗄️ Database Architecture
- **Primary Database**: **SQLite 3** (`instance/database.db`) for development; **PostgreSQL** with connection pooling for production.
- **Models**:
  - `User`: Account credentials, risk profile preferences, Google OAuth mappings.
  - `Portfolio`: User-isolated investment portfolios with health metrics.
  - `Holding`: Realized/unrealized holdings, weighted average cost basis, real-time allocation %.
  - `Transaction`: Immutable audit ledger for buy/sell order execution.
  - `Watchlist`: User-scoped tracked equities with uniqueness constraints.
  - `AIAnalysisCache`: Cached quantitative evaluations with expiration timestamps.

### 📡 External Market Data Providers
- **Live Equities & Fundamentals**: **Yahoo Finance** via [`yfinance`](https://github.com/ranaroussi/yfinance) (Live quotes, 52-week channels, P/E, ROE, debt ratios, EPS).
- **News Sentiment Feeds**: Google News RSS with topic-filtered ticker parsing.

---

## 🎯 7-Pillar Quantitative Scoring Engine

GetStockIQ evaluates Indian equities across 7 fundamental and technical pillars to produce a deterministic composite score ($0–100$):

$$\text{Composite Score} = 0.25\text{Fund} + 0.20\text{Tech} + 0.15\text{Val} + 0.15\text{Mom} + 0.10\text{Sent} + 0.10\text{Risk} + 0.05\text{Liq}$$

| Pillar | Weight | Key Metrics Evaluated |
| :--- | :---: | :--- |
| **Fundamentals** | **25%** | ROE, ROCE, Profit Margin, Debt-to-Equity, Solvency, Operating Cash Flow |
| **Technicals** | **20%** | Moving Averages (50 DMA / 200 DMA), RSI (14-day), MACD, Bollinger Bands |
| **Valuation** | **15%** | P/E Ratio, Forward P/E, PEG Ratio, P/B Ratio, EV/EBITDA, Dividend Yield |
| **Momentum** | **15%** | Multi-timeframe Returns (1M, 3M, 6M, 1Y), 52-Week Range Channel |
| **Sentiment** | **10%** | News Sentiment Analysis and Market Headline Tone Scoring |
| **Risk Resilience** | **10%** | Volatility (Beta), Max Drawdown, ATR %, Leverage Exposure |
| **Liquidity** | **5%** | Daily Rupee Turnover, Free-Float Market Capitalization |

### 🚦 Signal Classification:
* **Score $\ge 80$** $\to$ **Strong Buy** 🟢
* **Score $65 - 79$** $\to$ **Buy** 🟢
* **Score $50 - 64$** $\to$ **Hold** 🟡
* **Score $35 - 49$** $\to$ **Reduce** 🟠
* **Score $< 35$** $\to$ **Avoid** 🔴

---

## 🤖 Zero-Hallucination AI Architecture

- **Multi-Model LLM Gateway (`LLMService`)**:
  - Primary Model: `openai/gpt-4o-mini`
  - Automatic Fallback Chain: `anthropic/claude-3.5-haiku` $\to$ `google/gemini-2.5-flash` $\to$ `Deterministic Rule Template`
  - **Ground Truth Enforcement**: Mathematical calculations are 100% computed by the Python backend first. `VerifiedContextBuilder` feeds immutable numbers into read-only system prompts, ensuring the AI acts strictly as an explainer and never invents prices or ratings.

---

## ✨ Key Features

- 📊 **Executive Dashboard**: Real-time portfolio net worth, 24h P&L, asset allocation breakdown (Equities, Debt, Gold, Cash), and top market movers.
- 🔍 **Dynamic Stock Search**: Instant symbol and company lookup across Indian equities (`.NS` / `.BO`).
- 📈 **Quantitative Stock Analysis (`/analysis`)**: Comprehensive 7-pillar radar ratings, valuation multiples, and technical momentum charts.
- ⚖️ **Multi-Stock Comparison (`/compare`)**: Side-by-side comparative analysis of up to 3 stocks with highlighted winner badges.
- 💼 **Portfolio Manager (`/portfolio`)**: Weighted average cost basis tracking, trade logging (Buy/Sell), realized/unrealized P&L, and CSV export.
- 🛡️ **Automated AI Health Check**: One-click portfolio diagnostic auditing sector over-concentration and generating actionable rebalancing advice.
- 🤖 **Conversational AI Assistant (`/api/ask-ai`)**: Context-aware natural-language market intelligence chatbot.
- 🔐 **Enterprise Security**: Salted PBKDF2 password hashing, Google OAuth 2.0 Sign-In, 6-digit OTP password recovery, and CSRF protection.

---

## 🚀 Getting Started

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/harshitsharma1845/GetStocksIQ.git
cd GetStocksIQ

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the project root:
```env
SECRET_KEY=your-secure-random-secret
DATABASE_URL=sqlite:///database.db
OPENROUTER_API_KEY=your-openrouter-api-key
LLM_PRIMARY_MODEL=openai/gpt-4o-mini
LLM_FALLBACK_MODELS=anthropic/claude-3.5-haiku,google/gemini-2.5-flash,openai/gpt-4o
LLM_TIMEOUT=12
LLM_MAX_RETRIES=1
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### 3. Run Application
```bash
python app.py
```
Open **[http://localhost:5000](http://localhost:5000)** in your browser.

---

## 🧪 Testing

Run the full automated test suite:
```bash
python -m unittest discover -s tests -v
```

---

## ⚠️ Disclaimer

This application is developed for educational and quantitative research purposes only. Numerical calculations and qualitative research summaries do not constitute financial advice. Conduct independent due diligence before making capital investment decisions.

---

## 👤 Author & Maintainer

**Harshit Sharma**  
* GitHub: [@harshitsharma1845](https://github.com/harshitsharma1845)  
* Repository: [harshitsharma1845/GetStocksIQ](https://github.com/harshitsharma1845/GetStocksIQ)
