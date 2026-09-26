# 🚀 GetStockIQ — Complete Technical Architecture & System Documentation

> **Intelligent Multi-Factor Market Strategist & Portfolio Optimization Platform**  
> **Repository:** [harshitsharma1845/GetStocksIQ](https://github.com/harshitsharma1845/GetStocksIQ)  
> **Author & Maintainer:** Harshit Sharma (@harshitsharma1845)  
> **Documentation Release:** August 2026  
> **Generated PDF Report:** [`Stratix_AI_Complete_Documentation.pdf`](file:///d:/GetStockIQ/Stratix_AI_Complete_Documentation.pdf)

---

## 1. Executive Summary & Vision

**GetStockIQ** is a production-grade, multi-factor algorithmic market strategist and portfolio optimization web platform engineered specifically for Indian equities (NSE/BSE). It democratizes institutional-grade quantitative research, automated portfolio health checkups, real-time market data streaming, and conversational AI intelligence into an intuitive, glassmorphic digital experience.

---

## 2. Technology Stack & Why Each Tool Was Chosen

| Layer / Component | Technology Selected | Rationale & Strategic Value |
| :--- | :--- | :--- |
| **Backend Core** | **Python 3.13 + Flask 3.x** | Microsecond WSGI routing overhead, zero async lock-in, effortless integration with quantitative Python libraries (NumPy, Pandas, yfinance). |
| **Market Data Engine** | **yfinance + In-Memory Fallback Cache** | Fetches live quotes, 52-week price bands, EPS, P/E, volume, historical price trajectories, and sector metrics with resilient fallback against API throttling. |
| **Frontend Architecture** | **HTML5, CSS3 (Custom Glassmorphism), Vanilla JS (ES6+)** | Zero heavy bundler lock-in (no node_modules bloat), 60fps native GPU-accelerated rendering, fast first contentful paint (FCP), and smooth DOM hydration. |
| **UI Design System** | **Royal Purple Aesthetic (`#7c3aed`, `#5b21b6`) + Bootstrap Icons** | Modern frosted glass surfaces, dynamic radial gradients, floating levitation physics, and pixel-crisp iconography. |
| **Animation Engine** | **IntersectionObserver + Native SVG Stroke Offsets** | GPU-accelerated scroll reveals, animated stat counters (`0 -> Target`), pulsating radar indicators, and self-drawing SVG bezier paths without heavy dependencies. |
| **Security & Auth** | **PBKDF2-SHA256 & HTTP-Only Secure Sessions** | Cryptographically salted password hashing via Werkzeug, CSRF-safe forms, and 6-digit OTP verification flows for password recovery. |
| **AI Strategy Engine** | **Multi-Factor Heuristic & Diagnostic Engine** | Evaluates portfolio beta, Sharpe ratio, diversification score, asset weights, and generates natural-language investment recommendations. |

---

## 3. High-Level Architecture & Lifecycle Workflow

```
       ┌────────────────────────────────────────────────────────┐
       │             Browser Client (Mobile & Desktop)          │
       │   Vanilla JS ES6 • Glassmorphism CSS • SVG Animations  │
       └─────────────────────────┬──────────────────────────────┘
                                 │ HTTP/JSON
                                 ▼
       ┌────────────────────────────────────────────────────────┐
       │                  Flask WSGI Router                     │
       │   Session Auth (@login_required) • Input Sanitization  │
       └──────────────┬──────────────────────────┬──────────────┘
                      │                          │
        ┌─────────────▼────────────┐    ┌────────▼─────────────┐
        │  Financial Data Engine   │    │ AI Diagnostic Engine │
        │   yfinance + Fallback    │    │ Multi-Factor Rules   │
        └─────────────┬────────────┘    └────────┬─────────────┘
                      │                          │
                      └─────────────┬────────────┘
                                    ▼
       ┌────────────────────────────────────────────────────────┐
       │              Data Model & Session Store                │
       │   Users • Portfolios • Watchlists • OTP Verification   │
       └────────────────────────────────────────────────────────┘
```

---

## 4. Complete Module & Feature Breakdown

### 4.1 Interactive Landing Page & Conversion Funnel
* **Morphing Floating Pill Navbar**: Scroll detection triggers compact floating pill navigation with glassmorphism blur and smooth CTA button transition.
* **Hero Section**: High-impact value proposition, live market badges, dynamic starfield particle effects, and staggered entrance animations.
* **Insights Showcase**: Dual-layer stacked area SVG chart (*GetStockIQ Alpha Strategy* vs *NIFTY 50 Benchmark*) with live radar pulse, live ticker counter, and compact quarterly growth bars.
* **Performance Showcase**: Clean, balanced diagonal layout displaying Strategy Annualized Yield (`+34.6%`), sector breakdown tracks, and real-time asset sync.
* **Assistant Map**: Symmetrical 2x2 grid highlighting Personalized Signals, Smart Risk Checks, Portfolio Monitoring, and Market Alerts orbiting a glowing central AI core.

### 4.2 Authentication & Security Infrastructure
* **User Registration & Login**: Input sanitization, password strength validation, and secure session management.
* **OTP-Based Password Recovery**: Integrated 6-digit one-time password verification flow for seamless and secure credential resets.
* **Route Protection**: Unauthorized access automatically redirects users back to requested URLs post-authentication.

### 4.3 Comprehensive Dashboard & Portfolio Analytics
* **Valuation Overview**: Aggregate portfolio net worth, daily P&L fluctuations, total unrealized gains, and cash reserves.
* **Asset Allocation Visualizer**: Dynamic multi-asset breakdown covering Equities (Large/Mid/Small Cap), Debt Instruments, Gold, and Liquid Cash.
* **AI Portfolio Health Check**: One-click AI health diagnostics calculating risk-adjusted returns, diversification indices, and rebalancing recommendations.

### 4.4 Stock Discovery, Watchlist & Real-Time Tracking
* **Instant Search Autocomplete**: Low-latency stock lookup with live symbol matching across major Indian tickers (`RELIANCE`, `TCS`, `INFY`, `HDFCBANK`, etc.).
* **Custom Watchlist Manager**: Add/remove stocks with one tap, real-time price change badges (green/red indicators), and sector categorization.

### 4.5 Multi-Factor Stock Analysis & Comparison Matrix
* **Deep Stock Analysis Engine**: Detailed valuation multiples (P/E, P/B, EV/EBITDA), 52-week price bands, financial health scores, and technical momentum.
* **Head-to-Head Stock Comparison**: Side-by-side comparative table evaluating multiple stocks across market cap, revenue growth, operating margins, and algorithmic ratings.

### 4.6 Conversational AI Market Assistant
* **Context-Aware AI Endpoint (`/api/ask-ai`)**: Responds to conversational financial questions, explains complex market movements, and generates personalized stock insights based on user risk profiles.

### 4.7 User Profile & Settings Management
* **Compacted & Modernized Profile Hub**: Clean avatar card, streamlined security credentials, personalized risk tolerance selectors, and instant toggle switches for automated alerts.

### 4.8 Mobile-First Responsive Experience
* **Bottom Navigation Bar**: Native app-like thumb-accessible bottom tab navigation on mobile screens.
* **Touch-Optimized Targets**: 44px+ minimum touch targets, responsive card grids, and safe-area padding for modern iOS and Android devices.

---

## 5. Verified API & Route Specification

| Method & Route | Auth Required | Description & Functionality |
| :--- | :---: | :--- |
| `GET /` | No | Landing page with interactive SVG charts, feature showcases, and marketing funnels. |
| `GET /login`, `GET /register` | No | Authentication interfaces with client-side and server-side validation. |
| `GET /forgot-password` | No | Password recovery flow with email and OTP verification steps. |
| `GET /dashboard` | Yes | Central executive command dashboard with portfolio metrics and market movers. |
| `GET /portfolio` | Yes | Detailed portfolio holdings breakdown, asset allocation charts, and trade actions. |
| `GET /watchlist` | Yes | User customized stock watchlist with live pricing and sector badges. |
| `GET /compare` | Yes | Stock comparison picker and comparison result analysis matrix. |
| `GET /analysis?symbol=...` | Yes | Individual stock deep-dive factor analysis with valuation metrics. |
| `POST /api/ask-ai` | Yes | Conversational AI stock query assistant endpoint. |
| `POST /api/portfolio/ai-analysis` | Yes | Multi-factor portfolio health diagnostic algorithm endpoint. |
| `GET /api/search-stocks?q=...` | No | Fast autocomplete search querying ticker database. |

---

## 6. Local Setup & Execution Guide

```bash
# 1. Clone the repository
git clone https://github.com/harshitsharma1845/GetStocksIQ.git
cd GetStocksIQ

# 2. Create and activate a Python virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. Install required dependencies
pip install -r requirements.txt

# 4. Start the development server
python app.py
```
Open **`http://127.0.0.1:5000/`** in your browser.

---

## 7. Summary & Deliverables

GetStockIQ is a complete, scalable, and responsive financial web application that seamlessly marries cutting-edge quantitative analytics with an ultra-sleek, modern interface.
