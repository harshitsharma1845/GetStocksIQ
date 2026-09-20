import { useState, useEffect, useRef } from "react";

// ── Sparkline SVG ──────────────────────────────────────────────────────────
const Sparkline = ({ data, color = "#22C55E", width = 80, height = 32 }) => {
  const min = Math.min(...data), max = Math.max(...data);
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / (max - min || 1)) * height;
    return `${x},${y}`;
  }).join(" ");
  const area = `M0,${height} L${pts.split(" ").map(p => p).join(" L")} L${width},${height} Z`;
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ overflow: "visible" }}>
      <defs>
        <linearGradient id={`sg-${color.replace("#","")}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`M${area}`} fill={`url(#sg-${color.replace("#","")})`} />
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
};

// ── Gauge Chart ────────────────────────────────────────────────────────────
const Gauge = ({ value, max = 100, color = "#2563EB", size = 80 }) => {
  const r = 28, cx = 40, cy = 40;
  const circ = 2 * Math.PI * r;
  const pct = value / max;
  const dash = pct * circ * 0.75;
  const offset = circ * 0.125;
  return (
    <svg width={size} height={size} viewBox="0 0 80 80">
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8"
        strokeDasharray={`${circ * 0.75} ${circ * 0.25}`} strokeDashoffset={-offset} strokeLinecap="round" />
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth="8"
        strokeDasharray={`${dash} ${circ - dash}`} strokeDashoffset={-offset} strokeLinecap="round"
        style={{ transition: "stroke-dasharray 1s ease" }} />
      <text x={cx} y={cy + 5} textAnchor="middle" fill="white" fontSize="13" fontWeight="700">{value}</text>
    </svg>
  );
};

// ── Mini Donut ─────────────────────────────────────────────────────────────
const DonutChart = ({ data }) => {
  const total = data.reduce((s, d) => s + d.value, 0);
  let start = -Math.PI / 2;
  const r = 45, cx = 60, cy = 60;
  const slices = data.map(d => {
    const angle = (d.value / total) * 2 * Math.PI;
    const x1 = cx + r * Math.cos(start), y1 = cy + r * Math.sin(start);
    start += angle;
    const x2 = cx + r * Math.cos(start), y2 = cy + r * Math.sin(start);
    const large = angle > Math.PI ? 1 : 0;
    return { ...d, path: `M${cx},${cy} L${x1},${y1} A${r},${r} 0 ${large},1 ${x2},${y2} Z` };
  });
  return (
    <svg width="120" height="120" viewBox="0 0 120 120">
      <circle cx={cx} cy={cy} r={r - 14} fill="#111827" />
      {slices.map((s, i) => <path key={i} d={s.path} fill={s.color} opacity="0.9" />)}
    </svg>
  );
};

// ── Candlestick Chart ──────────────────────────────────────────────────────
const CandleChart = ({ candles = [], height = 200 }) => {
  const padding = 16;
  const w = 560, h = height;
  const prices = candles.flatMap(c => [c.h, c.l]);
  const minP = Math.min(...prices), maxP = Math.max(...prices);
  const scaleY = v => padding + ((maxP - v) / (maxP - minP)) * (h - padding * 2);
  const candleW = (w / candles.length) * 0.6;
  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} style={{ height: h }}>
      {candles.map((c, i) => {
        const x = (i / candles.length) * w + (w / candles.length) * 0.2;
        const isGreen = c.c >= c.o;
        const color = isGreen ? "#22C55E" : "#EF4444";
        const bodyTop = scaleY(Math.max(c.o, c.c));
        const bodyH = Math.abs(scaleY(c.o) - scaleY(c.c)) || 1;
        return (
          <g key={i}>
            <line x1={x + candleW / 2} y1={scaleY(c.h)} x2={x + candleW / 2} y2={scaleY(c.l)} stroke={color} strokeWidth="1" />
            <rect x={x} y={bodyTop} width={candleW} height={bodyH} fill={color} rx="1" />
          </g>
        );
      })}
    </svg>
  );
};

// ── Mock Data ──────────────────────────────────────────────────────────────
const sp1 = [22, 24, 21, 26, 23, 28, 25, 30, 28, 33];
const sp2 = [40, 38, 42, 39, 35, 37, 34, 36, 33, 31];
const sp3 = [15, 17, 16, 18, 20, 19, 22, 21, 24, 26];

const markets = [
  { name: "NIFTY 50", price: "22,834.20", change: "+0.87%", up: true, data: sp1 },
  { name: "SENSEX", price: "75,410.39", change: "+0.92%", up: true, data: sp3 },
  { name: "BANK NIFTY", price: "48,921.15", change: "-0.34%", up: false, data: sp2 },
  { name: "NASDAQ", price: "18,271.86", change: "+1.23%", up: true, data: sp1 },
  { name: "S&P 500", price: "5,460.48", change: "+0.71%", up: true, data: sp3 },
  { name: "Bitcoin", price: "$67,234.00", change: "+2.14%", up: true, data: sp1 },
  { name: "Gold", price: "$2,341.80", change: "-0.18%", up: false, data: sp2 },
  { name: "USD/INR", price: "83.48", change: "+0.06%", up: true, data: sp3 },
];

const recommendations = {
  buy: [
    { name: "Infosys", ticker: "INFY", confidence: 92, aiScore: 88, risk: 32, return: "18%", horizon: "6M", sector: "IT" },
    { name: "HDFC Bank", ticker: "HDFCBANK", confidence: 87, aiScore: 85, risk: 28, return: "14%", horizon: "12M", sector: "Banking" },
    { name: "Reliance Ind.", ticker: "RELIANCE", confidence: 84, aiScore: 82, risk: 35, return: "22%", horizon: "6M", sector: "Energy" },
  ],
  sell: [
    { name: "Adani Ports", ticker: "ADANIPORTS", confidence: 78, aiScore: 71, risk: 68, return: "-8%", horizon: "3M", sector: "Infra" },
    { name: "Paytm", ticker: "PAYTM", confidence: 81, aiScore: 74, risk: 72, return: "-12%", horizon: "1M", sector: "FinTech" },
  ],
  hold: [
    { name: "TCS", ticker: "TCS", confidence: 80, aiScore: 79, risk: 40, return: "9%", horizon: "3M", sector: "IT" },
    { name: "Wipro", ticker: "WIPRO", confidence: 75, aiScore: 73, risk: 42, return: "7%", horizon: "6M", sector: "IT" },
  ],
};

const agents = [
  { icon: "📊", name: "Market Agent", status: "active", conf: 94, output: "Bullish momentum detected in large-caps", color: "#2563EB" },
  { icon: "📰", name: "News Sentiment", status: "active", conf: 87, output: "Positive sentiment: 68% news bullish", color: "#8B5CF6" },
  { icon: "📈", name: "Technical Analysis", status: "active", conf: 91, output: "RSI 58, MACD bullish crossover on NIFTY", color: "#06B6D4" },
  { icon: "📉", name: "Fundamental Analysis", status: "processing", conf: 83, output: "PE ratios normalising; value emerging in IT", color: "#F59E0B" },
  { icon: "🌍", name: "Macro Economy", status: "active", conf: 79, output: "RBI hold; US Fed pivot expected Q3 2026", color: "#22C55E" },
  { icon: "💰", name: "Portfolio Optimizer", status: "active", conf: 96, output: "Optimal Sharpe: 2.34 at 60/30/10 mix", color: "#EC4899" },
  { icon: "⚠️", name: "Risk Assessment", status: "active", conf: 88, output: "Portfolio VaR (95%): ₹42,800 / day", color: "#EF4444" },
  { icon: "🤖", name: "Final Decision", status: "processing", conf: 90, output: "Aggregating signals — recommendation pending", color: "#F97316" },
];

const holdings = [
  { name: "Infosys", ticker: "INFY", qty: 120, price: 1834.50, change: 2.4, value: 220140, alloc: 28 },
  { name: "HDFC Bank", ticker: "HDFCBANK", qty: 85, price: 1720.30, change: 1.1, value: 146225, alloc: 19 },
  { name: "Reliance", ticker: "RELIANCE", qty: 60, price: 2945.60, change: -0.8, value: 176736, alloc: 23 },
  { name: "TCS", ticker: "TCS", qty: 40, price: 3812.75, change: 0.6, value: 152510, alloc: 20 },
  { name: "Bajaj Finance", ticker: "BAJFINANCE", qty: 25, price: 6834.20, change: -1.3, value: 170855, alloc: 10 },
];

const watchlist = [
  { name: "Asian Paints", ticker: "ASIANPAINT", price: 2845.30, change: 1.2, vol: "2.1M", mcap: "2.7T", data: sp1 },
  { name: "Maruti Suzuki", ticker: "MARUTI", price: 12340.50, change: -0.5, vol: "0.8M", mcap: "3.7T", data: sp2 },
  { name: "Sun Pharma", ticker: "SUNPHARMA", price: 1567.80, change: 2.8, vol: "3.4M", mcap: "3.8T", data: sp3 },
  { name: "Titan Company", ticker: "TITAN", price: 3421.60, change: 0.9, vol: "1.2M", mcap: "3.0T", data: sp1 },
  { name: "Kotak Bank", ticker: "KOTAKBANK", price: 1834.40, change: -1.1, vol: "4.5M", mcap: "3.6T", data: sp2 },
];

const news = [
  { headline: "RBI Keeps Rates Unchanged; Growth Forecast Revised to 7.2%", source: "Economic Times", sentiment: "bullish", time: "2h ago", tags: ["Macro", "Banking"] },
  { headline: "Infosys Q4 Results Beat Estimates; Raises FY27 Guidance", source: "Mint", sentiment: "bullish", time: "4h ago", tags: ["IT", "Earnings"] },
  { headline: "Global Oil Prices Dip on Demand Concerns; OPEC+ Meeting Eyed", source: "Bloomberg", sentiment: "bearish", time: "5h ago", tags: ["Energy", "Macro"] },
  { headline: "Paytm Faces Regulatory Scrutiny Over KYC Compliance Issues", source: "Reuters", sentiment: "bearish", time: "6h ago", tags: ["FinTech", "Regulatory"] },
  { headline: "Nifty IT Hits 52-Week High as US Tech Rally Spills Over", source: "NDTV Profit", sentiment: "bullish", time: "8h ago", tags: ["IT", "Markets"] },
  { headline: "Gold Edges Lower as Dollar Strengthens Post Jobs Data", source: "LiveMint", sentiment: "neutral", time: "9h ago", tags: ["Commodities"] },
];

const generateCandles = (n = 60) =>
  Array.from({ length: n }, (_, i) => {
    const base = 22000 + Math.sin(i / 5) * 800 + i * 12 + Math.random() * 200;
    const o = base + Math.random() * 100 - 50;
    const c = base + Math.random() * 200 - 100;
    return { o, c, h: Math.max(o, c) + Math.random() * 80, l: Math.min(o, c) - Math.random() * 80 };
  });

const candles = generateCandles(50);

const chatHistory = [
  { role: "ai", text: "Hello! I'm your AI Investment Strategist. Ask me anything about stocks, portfolios, or market trends." },
  { role: "user", text: "What's your view on IT sector for next 6 months?" },
  { role: "ai", text: "The IT sector looks **promising** for H2 2026. Key drivers: (1) US Fed rate cuts improving client budgets, (2) AI-related deal flow accelerating at TCS & Infosys, (3) Rupee depreciation benefiting export earnings. I'd recommend **accumulating INFY and TCS** on dips. Target: 15–20% upside in 6M with moderate risk (Risk Score: 38/100)." },
];

// ── App ────────────────────────────────────────────────────────────────────
export default function App() {
  const [activePage, setActivePage] = useState("dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [messages, setMessages] = useState(chatHistory);
  const [recTab, setRecTab] = useState("buy");
  const [chartFilter, setChartFilter] = useState("1M");
  const [screenerFilters, setScreenerFilters] = useState({ sector: "All", mcap: "All" });
  const [numbers, setNumbers] = useState({ portfolio: 0, gain: 0 });
  const chatEndRef = useRef(null);
  const [agentProgress, setAgentProgress] = useState(agents.map(() => 0));

  useEffect(() => {
    const t = setTimeout(() => setNumbers({ portfolio: 865466, gain: 12840 }), 400);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    const intervals = agents.map((_, i) =>
      setInterval(() => {
        setAgentProgress(prev => {
          const next = [...prev];
          next[i] = (next[i] + (Math.random() * 3)) % 100;
          return next;
        });
      }, 800 + i * 200)
    );
    return () => intervals.forEach(clearInterval);
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, chatOpen]);

  const sendMessage = () => {
    if (!chatInput.trim()) return;
    const userMsg = { role: "user", text: chatInput };
    const aiMsg = { role: "ai", text: "Analyzing your query using real-time market data and multi-agent signals… Based on current conditions, here's my assessment: markets show resilience with strong institutional buying. I recommend reviewing your allocation and considering a **systematic approach** to rebalancing." };
    setMessages(m => [...m, userMsg, aiMsg]);
    setChatInput("");
  };

  const navItems = [
    { id: "dashboard", icon: "⬛", label: "Dashboard" },
    { id: "markets", icon: "📊", label: "Markets" },
    { id: "agents", icon: "🤖", label: "AI Agents" },
    { id: "portfolio", icon: "💼", label: "Portfolio" },
    { id: "watchlist", icon: "👁", label: "Watchlist" },
    { id: "recommendations", icon: "🎯", label: "Recommendations" },
    { id: "news", icon: "📰", label: "News" },
    { id: "screener", icon: "🔍", label: "Screener" },
    { id: "risk", icon: "⚠️", label: "Risk Analysis" },
    { id: "alerts", icon: "🔔", label: "Alerts" },
    { id: "settings", icon: "⚙️", label: "Settings" },
  ];

  const css = `
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Inter', sans-serif; background: #0B1220; color: #E2E8F0; }
    ::-webkit-scrollbar { width: 4px; height: 4px; }
    ::-webkit-scrollbar-track { background: #0B1220; }
    ::-webkit-scrollbar-thumb { background: #1E3A5F; border-radius: 4px; }
    .glass { background: rgba(255,255,255,0.04); backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.08); }
    .glass-card { background: #111827; border: 1px solid rgba(255,255,255,0.07); border-radius: 16px; }
    .gradient-btn { background: linear-gradient(135deg, #2563EB, #1D4ED8); transition: all 0.2s; }
    .gradient-btn:hover { background: linear-gradient(135deg, #1D4ED8, #1E40AF); transform: translateY(-1px); box-shadow: 0 8px 24px rgba(37,99,235,0.4); }
    .card-hover { transition: transform 0.2s, box-shadow 0.2s; }
    .card-hover:hover { transform: translateY(-3px); box-shadow: 0 12px 32px rgba(0,0,0,0.4); }
    .pulse { animation: pulse 2s infinite; }
    @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.5; } }
    .spin { animation: spin 3s linear infinite; }
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    .fade-in { animation: fadeIn 0.5s ease; }
    @keyframes fadeIn { from { opacity:0; transform: translateY(10px); } to { opacity:1; transform: none; } }
    .gradient-text { background: linear-gradient(135deg, #60A5FA, #818CF8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
    .gradient-text-green { background: linear-gradient(135deg, #34D399, #22C55E); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
    .sidebar-item { border-radius: 10px; cursor: pointer; transition: all 0.18s; }
    .sidebar-item:hover { background: rgba(37,99,235,0.15); }
    .sidebar-item.active { background: rgba(37,99,235,0.25); border-left: 3px solid #2563EB; }
    .agent-glow { box-shadow: 0 0 20px rgba(37,99,235,0.2); }
    .tag { font-size: 10px; padding: 2px 8px; border-radius: 99px; font-weight: 600; }
    .number-count { transition: all 0.8s cubic-bezier(0.34,1.56,0.64,1); }
    @keyframes float { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
    .float { animation: float 4s ease-in-out infinite; }
    .progress-bar { height: 4px; border-radius: 4px; background: rgba(255,255,255,0.08); overflow: hidden; }
    .progress-fill { height: 100%; border-radius: 4px; transition: width 0.6s ease; }
    input, select { outline: none; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: #E2E8F0; border-radius: 10px; padding: 8px 14px; font-family: 'Inter', sans-serif; font-size: 14px; }
    input:focus, select:focus { border-color: #2563EB; }
    select option { background: #111827; }
    .badge { font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 99px; text-transform: uppercase; letter-spacing: 0.5px; }
    @media (max-width: 768px) { .sidebar-desktop { display: none !important; } .main-content { margin-left: 0 !important; } }
  `;

  // ── Sections ───────────────────────────────────────────────────────────
  const renderDashboard = () => (
    <div className="fade-in" style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Hero */}
      <div className="glass-card" style={{ padding: "32px 40px", background: "linear-gradient(135deg, rgba(37,99,235,0.15) 0%, rgba(139,92,246,0.1) 100%)", position: "relative", overflow: "hidden" }}>
        <div style={{ position: "absolute", right: 40, top: "50%", transform: "translateY(-50%)", opacity: 0.15, fontSize: 120 }} className="float">🤖</div>
        <div style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, background: "radial-gradient(ellipse at 70% 50%, rgba(37,99,235,0.1) 0%, transparent 60%)" }} />
        <div style={{ position: "relative", zIndex: 1 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: "#60A5FA", letterSpacing: 2, textTransform: "uppercase", marginBottom: 8 }}>⚡ Powered by 8 Specialized AI Agents</div>
          <h1 style={{ fontSize: 36, fontWeight: 900, lineHeight: 1.2, marginBottom: 8 }}>
            <span className="gradient-text">AI Investment Strategist</span>
          </h1>
          <p style={{ color: "#94A3B8", fontSize: 16, marginBottom: 24 }}>Multi-Agent Financial Intelligence Platform — Real-time analysis across 5,000+ instruments</p>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {["📈 Analyze Stock", "💼 Build Portfolio", "🎯 AI Recommendation", "💬 Ask AI"].map((btn, i) => (
              <button key={i} className={i === 0 ? "gradient-btn" : ""} onClick={() => i === 3 && setChatOpen(true)}
                style={{ padding: "10px 20px", borderRadius: 10, border: i === 0 ? "none" : "1px solid rgba(255,255,255,0.15)", background: i === 0 ? "" : "rgba(255,255,255,0.05)", color: "white", cursor: "pointer", fontSize: 14, fontWeight: 600, transition: "all 0.2s" }}>
                {btn}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Market Overview */}
      <div>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 14, color: "#F1F5F9" }}>Market Overview</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 12 }}>
          {markets.map((m, i) => (
            <div key={i} className="glass-card card-hover" style={{ padding: "16px 18px" }}>
              <div style={{ fontSize: 11, color: "#94A3B8", fontWeight: 600, marginBottom: 4 }}>{m.name}</div>
              <div style={{ fontSize: 17, fontWeight: 800, color: "#F1F5F9", marginBottom: 2 }}>{m.price}</div>
              <div style={{ fontSize: 12, fontWeight: 700, color: m.up ? "#22C55E" : "#EF4444", marginBottom: 10 }}>
                {m.up ? "▲" : "▼"} {m.change}
              </div>
              <Sparkline data={m.data} color={m.up ? "#22C55E" : "#EF4444"} />
            </div>
          ))}
        </div>
      </div>

      {/* Recommendations + Portfolio side by side */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 20 }}>
        {/* Rec */}
        <div className="glass-card" style={{ padding: 24 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
            <h2 style={{ fontSize: 17, fontWeight: 700 }}>🎯 AI Recommendations</h2>
            <div style={{ display: "flex", gap: 8 }}>
              {["buy", "sell", "hold"].map(t => (
                <button key={t} onClick={() => setRecTab(t)}
                  style={{ padding: "6px 16px", borderRadius: 8, border: "none", cursor: "pointer", fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.5, background: recTab === t ? (t === "buy" ? "#22C55E" : t === "sell" ? "#EF4444" : "#F59E0B") : "rgba(255,255,255,0.07)", color: recTab === t ? "white" : "#94A3B8", transition: "all 0.2s" }}>
                  {t}
                </button>
              ))}
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {recommendations[recTab].map((r, i) => (
              <div key={i} className="card-hover" style={{ background: "rgba(255,255,255,0.03)", borderRadius: 12, padding: "16px 20px", border: "1px solid rgba(255,255,255,0.06)", display: "flex", alignItems: "center", gap: 16 }}>
                <div style={{ width: 44, height: 44, borderRadius: 12, background: "linear-gradient(135deg, #1E3A5F, #2563EB)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18, flexShrink: 0 }}>
                  {r.ticker[0]}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 14 }}>{r.name} <span style={{ color: "#64748B", fontWeight: 500, fontSize: 12 }}>{r.ticker}</span></div>
                  <div style={{ fontSize: 12, color: "#94A3B8", marginTop: 2 }}>{r.sector} · Horizon: {r.horizon}</div>
                  <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
                    <span style={{ fontSize: 11, color: "#94A3B8" }}>AI Score <strong style={{ color: "#60A5FA" }}>{r.aiScore}</strong></span>
                    <span style={{ fontSize: 11, color: "#94A3B8" }}>Risk <strong style={{ color: "#F59E0B" }}>{r.risk}</strong></span>
                    <span style={{ fontSize: 11, color: "#94A3B8" }}>Return <strong style={{ color: recTab === "sell" ? "#EF4444" : "#22C55E" }}>{r.return}</strong></span>
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: 22, fontWeight: 900, color: recTab === "buy" ? "#22C55E" : recTab === "sell" ? "#EF4444" : "#F59E0B" }}>{r.confidence}%</div>
                  <div style={{ fontSize: 10, color: "#64748B" }}>Confidence</div>
                  <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
                    <button className="gradient-btn" style={{ padding: "5px 12px", borderRadius: 7, border: "none", color: "white", fontSize: 11, fontWeight: 600, cursor: "pointer" }}>View</button>
                    <button style={{ padding: "5px 12px", borderRadius: 7, border: "1px solid rgba(255,255,255,0.15)", color: "#94A3B8", background: "transparent", fontSize: 11, cursor: "pointer" }}>+ WL</button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Portfolio mini */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="glass-card" style={{ padding: 24 }}>
            <div style={{ fontSize: 12, color: "#94A3B8", fontWeight: 600, marginBottom: 4 }}>Total Portfolio Value</div>
            <div className="gradient-text-green" style={{ fontSize: 32, fontWeight: 900, marginBottom: 4 }}>
              ₹{numbers.portfolio.toLocaleString()}
            </div>
            <div style={{ color: "#22C55E", fontSize: 13, fontWeight: 700 }}>▲ +₹{numbers.gain.toLocaleString()} today (+1.5%)</div>
            <div style={{ marginTop: 20, display: "flex", justifyContent: "center" }}>
              <DonutChart data={[
                { value: 28, color: "#2563EB" }, { value: 19, color: "#22C55E" }, { value: 23, color: "#8B5CF6" }, { value: 20, color: "#F59E0B" }, { value: 10, color: "#EC4899" }
              ]} />
            </div>
            <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 6 }}>
              {[["Infosys", "#2563EB", 28], ["Reliance", "#8B5CF6", 23], ["TCS", "#F59E0B", 20], ["HDFC Bank", "#22C55E", 19], ["Bajaj", "#EC4899", 10]].map(([name, color, pct]) => (
                <div key={name} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div style={{ width: 10, height: 10, borderRadius: 3, background: color, flexShrink: 0 }} />
                  <div style={{ flex: 1, fontSize: 12, color: "#94A3B8" }}>{name}</div>
                  <div style={{ fontSize: 12, fontWeight: 700 }}>{pct}%</div>
                </div>
              ))}
            </div>
          </div>
          <div className="glass-card" style={{ padding: 20 }}>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12 }}>Overall Return</div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <div>
                <div style={{ fontSize: 24, fontWeight: 900, color: "#22C55E" }}>+34.8%</div>
                <div style={{ fontSize: 12, color: "#64748B" }}>Since Inception</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: 18, fontWeight: 800, color: "#F59E0B" }}>2.34</div>
                <div style={{ fontSize: 12, color: "#64748B" }}>Sharpe Ratio</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="glass-card" style={{ padding: 24 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16, flexWrap: "wrap", gap: 12 }}>
          <div>
            <div style={{ fontSize: 13, color: "#94A3B8" }}>NIFTY 50</div>
            <div style={{ fontSize: 24, fontWeight: 800 }}>22,834.20 <span style={{ fontSize: 14, color: "#22C55E", fontWeight: 700 }}>▲ +196.45 (+0.87%)</span></div>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {["1D","1W","1M","3M","1Y","5Y"].map(f => (
              <button key={f} onClick={() => setChartFilter(f)}
                style={{ padding: "5px 14px", borderRadius: 7, border: "none", cursor: "pointer", fontSize: 12, fontWeight: 700, background: chartFilter === f ? "#2563EB" : "rgba(255,255,255,0.07)", color: chartFilter === f ? "white" : "#94A3B8", transition: "all 0.2s" }}>{f}</button>
            ))}
            <span style={{ width: 1, background: "rgba(255,255,255,0.1)", margin: "0 4px" }} />
            {["RSI","MACD","EMA","BB"].map(ind => (
              <button key={ind} style={{ padding: "5px 10px", borderRadius: 7, border: "1px solid rgba(255,255,255,0.12)", cursor: "pointer", fontSize: 11, fontWeight: 600, background: "transparent", color: "#64748B" }}>{ind}</button>
            ))}
          </div>
        </div>
        <div style={{ overflowX: "auto" }}>
          <CandleChart candles={candles} height={220} />
        </div>
        {/* Volume */}
        <div style={{ height: 40, marginTop: 8 }}>
          <svg width="100%" viewBox="0 0 560 40" preserveAspectRatio="none">
            {candles.map((c, i) => (
              <rect key={i} x={(i / candles.length) * 560} y={40 - Math.random() * 30 - 5} width={560 / candles.length * 0.7} height={Math.random() * 30 + 5}
                fill={c.c >= c.o ? "rgba(34,197,94,0.4)" : "rgba(239,68,68,0.4)"} rx="1" />
            ))}
          </svg>
        </div>
      </div>

      {/* AI Agents */}
      <div className="glass-card" style={{ padding: 24 }}>
        <h2 style={{ fontSize: 17, fontWeight: 700, marginBottom: 20 }}>🤖 AI Multi-Agent System</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 14 }}>
          {agents.map((a, i) => (
            <div key={i} className="card-hover" style={{ background: "rgba(255,255,255,0.03)", borderRadius: 12, padding: 16, border: `1px solid ${a.color}22`, position: "relative", overflow: "hidden" }}>
              <div style={{ position: "absolute", top: 0, right: 0, width: 80, height: 80, background: `radial-gradient(circle at top right, ${a.color}15, transparent)` }} />
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
                <div style={{ fontSize: 24 }}>{a.icon}</div>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700 }}>{a.name}</div>
                  <div style={{ display: "flex", alignItems: "center", gap: 5, marginTop: 2 }}>
                    <div style={{ width: 7, height: 7, borderRadius: "50%", background: a.status === "active" ? "#22C55E" : "#F59E0B" }} className={a.status === "processing" ? "pulse" : ""} />
                    <span style={{ fontSize: 10, color: "#64748B", textTransform: "capitalize" }}>{a.status}</span>
                  </div>
                </div>
                <div style={{ marginLeft: "auto", fontSize: 18, fontWeight: 900, color: a.color }}>{a.conf}%</div>
              </div>
              <div className="progress-bar" style={{ marginBottom: 8 }}>
                <div className="progress-fill" style={{ width: `${agentProgress[i]}%`, background: `linear-gradient(90deg, ${a.color}88, ${a.color})` }} />
              </div>
              <div style={{ fontSize: 11, color: "#94A3B8", lineHeight: 1.5 }}>{a.output}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Watchlist + News */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: 20 }}>
        <div className="glass-card" style={{ padding: 24 }}>
          <h2 style={{ fontSize: 17, fontWeight: 700, marginBottom: 16 }}>👁 Watchlist</h2>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ color: "#64748B", fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5 }}>
                  {["Stock", "Price", "Change", "Volume", "MCap", "Trend"].map(h => (
                    <th key={h} style={{ padding: "6px 12px", textAlign: h === "Trend" ? "center" : "left", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {watchlist.map((w, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)", transition: "background 0.15s", cursor: "pointer" }}
                    onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,0.03)"}
                    onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                    <td style={{ padding: "12px 12px" }}>
                      <div style={{ fontWeight: 700 }}>{w.ticker}</div>
                      <div style={{ fontSize: 11, color: "#64748B" }}>{w.name}</div>
                    </td>
                    <td style={{ padding: "12px 12px", fontWeight: 700 }}>₹{w.price.toLocaleString()}</td>
                    <td style={{ padding: "12px 12px", color: w.change > 0 ? "#22C55E" : "#EF4444", fontWeight: 700 }}>
                      {w.change > 0 ? "▲" : "▼"} {Math.abs(w.change)}%
                    </td>
                    <td style={{ padding: "12px 12px", color: "#94A3B8" }}>{w.vol}</td>
                    <td style={{ padding: "12px 12px", color: "#94A3B8" }}>{w.mcap}</td>
                    <td style={{ padding: "12px 12px", textAlign: "center" }}>
                      <Sparkline data={w.data} color={w.change > 0 ? "#22C55E" : "#EF4444"} width={60} height={24} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="glass-card" style={{ padding: 24 }}>
          <h2 style={{ fontSize: 17, fontWeight: 700, marginBottom: 16 }}>📰 Market News</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {news.slice(0, 4).map((n, i) => (
              <div key={i} style={{ background: "rgba(255,255,255,0.03)", borderRadius: 10, padding: "12px 14px", border: "1px solid rgba(255,255,255,0.05)", cursor: "pointer", transition: "border-color 0.2s" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6, gap: 8 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, lineHeight: 1.4, flex: 1 }}>{n.headline}</div>
                  <span className="badge" style={{ background: n.sentiment === "bullish" ? "rgba(34,197,94,0.15)" : n.sentiment === "bearish" ? "rgba(239,68,68,0.15)" : "rgba(245,158,11,0.15)", color: n.sentiment === "bullish" ? "#22C55E" : n.sentiment === "bearish" ? "#EF4444" : "#F59E0B", flexShrink: 0 }}>
                    {n.sentiment}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: "#64748B" }}>{n.source} · {n.time}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );

  const renderPortfolio = () => (
    <div className="fade-in" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <h2 style={{ fontSize: 20, fontWeight: 800 }}>💼 Portfolio</h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 14 }}>
        {[
          { label: "Portfolio Value", val: "₹8,65,466", color: "#22C55E" },
          { label: "Today's Gain", val: "+₹12,840", color: "#22C55E" },
          { label: "Total Return", val: "+34.8%", color: "#22C55E" },
          { label: "Invested Value", val: "₹6,42,000", color: "#60A5FA" },
        ].map((s, i) => (
          <div key={i} className="glass-card" style={{ padding: "20px 22px" }}>
            <div style={{ fontSize: 11, color: "#64748B", fontWeight: 600, marginBottom: 6 }}>{s.label}</div>
            <div style={{ fontSize: 22, fontWeight: 900, color: s.color }}>{s.val}</div>
          </div>
        ))}
      </div>
      <div className="glass-card" style={{ padding: 24 }}>
        <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16 }}>Top Holdings</h3>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ color: "#64748B", fontSize: 11, fontWeight: 600, textTransform: "uppercase" }}>
              {["Stock", "Qty", "Avg Price", "CMP", "P&L", "Allocation"].map(h => (
                <th key={h} style={{ padding: "8px 12px", textAlign: "left", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {holdings.map((h, i) => (
              <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                <td style={{ padding: "14px 12px" }}><div style={{ fontWeight: 700 }}>{h.ticker}</div><div style={{ fontSize: 11, color: "#64748B" }}>{h.name}</div></td>
                <td style={{ padding: "14px 12px", color: "#94A3B8" }}>{h.qty}</td>
                <td style={{ padding: "14px 12px" }}>₹{h.price.toLocaleString()}</td>
                <td style={{ padding: "14px 12px", fontWeight: 700 }}>₹{(h.price * (1 + h.change / 100)).toFixed(2)}</td>
                <td style={{ padding: "14px 12px", color: h.change > 0 ? "#22C55E" : "#EF4444", fontWeight: 700 }}>
                  {h.change > 0 ? "+" : ""}{h.change}%
                </td>
                <td style={{ padding: "14px 12px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <div style={{ flex: 1, height: 6, background: "rgba(255,255,255,0.08)", borderRadius: 3, overflow: "hidden" }}>
                      <div style={{ width: `${h.alloc}%`, height: "100%", background: "#2563EB", borderRadius: 3 }} />
                    </div>
                    <span style={{ fontSize: 12, fontWeight: 700, width: 30 }}>{h.alloc}%</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  const renderRisk = () => (
    <div className="fade-in" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <h2 style={{ fontSize: 20, fontWeight: 800 }}>⚠️ Risk Analysis Dashboard</h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 16 }}>
        {[
          { label: "Portfolio Risk", val: 38, color: "#F59E0B", desc: "Moderate" },
          { label: "Volatility", val: 64, color: "#2563EB", desc: "Annualised 18.4%" },
          { label: "Sharpe Ratio", val: 78, color: "#22C55E", desc: "2.34" },
          { label: "Diversification", val: 82, color: "#8B5CF6", desc: "Well Diversified" },
          { label: "VaR (95%)", val: 45, color: "#EF4444", desc: "₹42,800 / day" },
          { label: "Max Drawdown", val: 28, color: "#EC4899", desc: "-14.2%" },
        ].map((r, i) => (
          <div key={i} className="glass-card card-hover" style={{ padding: 24, textAlign: "center" }}>
            <Gauge value={r.val} color={r.color} size={90} />
            <div style={{ marginTop: 10, fontWeight: 700, fontSize: 14 }}>{r.label}</div>
            <div style={{ fontSize: 12, color: r.color, fontWeight: 600, marginTop: 4 }}>{r.desc}</div>
          </div>
        ))}
      </div>
      <div className="glass-card" style={{ padding: 24 }}>
        <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16 }}>AI Workflow</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 0, maxWidth: 400, margin: "0 auto" }}>
          {["Market Data Ingestion", "News & Sentiment Analysis", "Technical Analysis", "Fundamental Analysis", "Risk Assessment", "Portfolio Optimization", "Final AI Recommendation"].map((step, i) => (
            <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 16 }}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                <div style={{ width: 32, height: 32, borderRadius: "50%", background: "linear-gradient(135deg, #2563EB, #8B5CF6)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 12, flexShrink: 0 }}>{i + 1}</div>
                {i < 6 && <div style={{ width: 2, height: 32, background: "linear-gradient(#2563EB44, #8B5CF644)", margin: "2px 0" }} />}
              </div>
              <div style={{ paddingTop: 6, paddingBottom: i < 6 ? 24 : 0 }}>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{step}</div>
                <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>Agent {i + 1} processing complete</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderAgents = () => (
    <div className="fade-in" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <h2 style={{ fontSize: 20, fontWeight: 800 }}>🤖 AI Agents — Live Dashboard</h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
        {agents.map((a, i) => (
          <div key={i} className="glass-card card-hover agent-glow" style={{ padding: 24, border: `1px solid ${a.color}33` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 16 }}>
              <div style={{ width: 52, height: 52, borderRadius: 14, background: `${a.color}22`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 26, border: `1px solid ${a.color}44` }}>{a.icon}</div>
              <div>
                <div style={{ fontWeight: 800, fontSize: 15 }}>{a.name}</div>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 3 }}>
                  <div style={{ width: 8, height: 8, borderRadius: "50%", background: a.status === "active" ? "#22C55E" : "#F59E0B" }} className={a.status === "processing" ? "pulse" : ""} />
                  <span style={{ fontSize: 11, color: "#64748B", textTransform: "capitalize" }}>{a.status}</span>
                </div>
              </div>
              <div style={{ marginLeft: "auto", textAlign: "right" }}>
                <div style={{ fontSize: 28, fontWeight: 900, color: a.color }}>{a.conf}%</div>
                <div style={{ fontSize: 10, color: "#64748B" }}>Confidence</div>
              </div>
            </div>
            <div style={{ marginBottom: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#64748B", marginBottom: 6 }}>
                <span>Processing</span><span>{Math.round(agentProgress[i])}%</span>
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${agentProgress[i]}%`, background: `linear-gradient(90deg, ${a.color}66, ${a.color})` }} />
              </div>
            </div>
            <div style={{ fontSize: 13, color: "#94A3B8", background: "rgba(255,255,255,0.03)", padding: "10px 12px", borderRadius: 8 }}>{a.output}</div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderNews = () => (
    <div className="fade-in" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <h2 style={{ fontSize: 20, fontWeight: 800 }}>📰 Market News & Sentiment</h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 16 }}>
        {news.map((n, i) => (
          <div key={i} className="glass-card card-hover" style={{ padding: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10, gap: 10 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, lineHeight: 1.4, flex: 1 }}>{n.headline}</h3>
              <span className="badge" style={{ background: n.sentiment === "bullish" ? "rgba(34,197,94,0.15)" : n.sentiment === "bearish" ? "rgba(239,68,68,0.15)" : "rgba(245,158,11,0.15)", color: n.sentiment === "bullish" ? "#22C55E" : n.sentiment === "bearish" ? "#EF4444" : "#F59E0B", flexShrink: 0 }}>
                {n.sentiment}
              </span>
            </div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
              {n.tags.map(t => <span key={t} className="tag" style={{ background: "rgba(37,99,235,0.15)", color: "#60A5FA" }}>{t}</span>)}
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 11, color: "#64748B" }}>{n.source} · {n.time}</span>
              <button className="gradient-btn" style={{ padding: "5px 14px", borderRadius: 7, border: "none", color: "white", fontSize: 11, fontWeight: 600, cursor: "pointer" }}>Read More</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderScreener = () => (
    <div className="fade-in" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <h2 style={{ fontSize: 20, fontWeight: 800 }}>🔍 Stock Screener</h2>
      <div className="glass-card" style={{ padding: 20 }}>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 20 }}>
          {[
            { label: "Sector", opts: ["All", "IT", "Banking", "Energy", "Pharma", "FMCG", "Auto"] },
            { label: "Market Cap", opts: ["All", "Large Cap", "Mid Cap", "Small Cap"] },
            { label: "PE Ratio", opts: ["All", "< 15", "15-30", "> 30"] },
            { label: "ROE", opts: ["All", "> 15%", "> 20%", "> 30%"] },
          ].map((f, i) => (
            <div key={i}>
              <div style={{ fontSize: 11, color: "#64748B", marginBottom: 4, fontWeight: 600 }}>{f.label}</div>
              <select style={{ minWidth: 130 }}>
                {f.opts.map(o => <option key={o}>{o}</option>)}
              </select>
            </div>
          ))}
          <div style={{ display: "flex", alignItems: "flex-end" }}>
            <button className="gradient-btn" style={{ padding: "9px 24px", borderRadius: 10, border: "none", color: "white", fontSize: 13, fontWeight: 700, cursor: "pointer" }}>Screen Stocks</button>
          </div>
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ color: "#64748B", fontSize: 11, fontWeight: 600, textTransform: "uppercase" }}>
              {["Stock", "Sector", "Price", "PE", "ROE", "EPS", "52W High", "52W Low", "AI Score"].map(h => (
                <th key={h} style={{ padding: "8px 12px", textAlign: "left", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[
              ["INFY", "IT", "₹1,834", "24.2", "27%", "76.2", "₹1,980", "₹1,320", 88],
              ["HDFCBANK", "Banking", "₹1,720", "18.4", "16%", "93.5", "₹1,880", "₹1,430", 85],
              ["RELIANCE", "Energy", "₹2,945", "26.8", "12%", "109.8", "₹3,200", "₹2,240", 82],
              ["TCS", "IT", "₹3,812", "28.6", "42%", "133.2", "₹4,080", "₹3,100", 79],
              ["SUNPHARMA", "Pharma", "₹1,567", "32.4", "19%", "48.4", "₹1,720", "₹1,100", 76],
            ].map((row, i) => (
              <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)", cursor: "pointer" }}
                onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,0.03)"}
                onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                {row.map((cell, j) => (
                  <td key={j} style={{ padding: "14px 12px", fontWeight: j === 0 ? 700 : 400, color: j === row.length - 1 ? "#60A5FA" : j === 2 ? "#F1F5F9" : "#94A3B8" }}>
                    {j === row.length - 1 ? <span style={{ background: "rgba(37,99,235,0.15)", padding: "3px 10px", borderRadius: 6, fontWeight: 800 }}>{cell}</span> : cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  const renderAlerts = () => (
    <div className="fade-in" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <h2 style={{ fontSize: 20, fontWeight: 800 }}>🔔 Alerts</h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
        {[
          { type: "Price Alert", icon: "💰", desc: "INFY crosses ₹1,900", active: true, color: "#22C55E" },
          { type: "AI Alert", icon: "🤖", desc: "Strong buy signal on HDFCBANK", active: true, color: "#2563EB" },
          { type: "Risk Alert", icon: "⚠️", desc: "Portfolio VaR exceeded threshold", active: false, color: "#EF4444" },
          { type: "News Alert", icon: "📰", desc: "Negative news for ADANIPORTS", active: true, color: "#F59E0B" },
          { type: "Volume Alert", icon: "📊", desc: "TCS volume 3x average", active: false, color: "#8B5CF6" },
          { type: "Email/SMS", icon: "📱", desc: "Configure delivery channels", active: true, color: "#EC4899" },
        ].map((a, i) => (
          <div key={i} className="glass-card card-hover" style={{ padding: 20 }}>
            <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
              <div style={{ width: 44, height: 44, borderRadius: 12, background: `${a.color}22`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22, border: `1px solid ${a.color}33` }}>{a.icon}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>{a.type}</div>
                <div style={{ fontSize: 13, color: "#94A3B8", marginBottom: 12 }}>{a.desc}</div>
                <div style={{ display: "flex", gap: 8 }}>
                  {["Email", "SMS", "Push"].map(ch => (
                    <span key={ch} className="tag" style={{ background: "rgba(255,255,255,0.07)", color: "#94A3B8", cursor: "pointer" }}>{ch}</span>
                  ))}
                </div>
              </div>
              <div style={{ width: 40, height: 22, borderRadius: 11, background: a.active ? "#22C55E" : "rgba(255,255,255,0.1)", position: "relative", cursor: "pointer", transition: "background 0.2s", flexShrink: 0 }}>
                <div style={{ position: "absolute", top: 3, left: a.active ? 20 : 3, width: 16, height: 16, borderRadius: "50%", background: "white", transition: "left 0.2s" }} />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderSettings = () => (
    <div className="fade-in" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <h2 style={{ fontSize: 20, fontWeight: 800 }}>⚙️ Settings</h2>
      <div style={{ display: "grid", gridTemplateColumns: "200px 1fr", gap: 20 }}>
        <div className="glass-card" style={{ padding: 16 }}>
          {["Profile", "Broker Integration", "Theme", "Notifications", "API Keys", "Security", "Language", "Currency"].map((s, i) => (
            <div key={i} style={{ padding: "10px 14px", borderRadius: 8, cursor: "pointer", color: i === 0 ? "#60A5FA" : "#94A3B8", fontWeight: i === 0 ? 700 : 500, fontSize: 14, background: i === 0 ? "rgba(37,99,235,0.12)" : "transparent", marginBottom: 2, transition: "all 0.15s" }}
              onMouseEnter={e => { if (i !== 0) e.currentTarget.style.background = "rgba(255,255,255,0.04)"; }}
              onMouseLeave={e => { if (i !== 0) e.currentTarget.style.background = "transparent"; }}>
              {s}
            </div>
          ))}
        </div>
        <div className="glass-card" style={{ padding: 28 }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 22 }}>Profile Settings</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 18, maxWidth: 400 }}>
            {[{ label: "Full Name", val: "Arjun Sharma" }, { label: "Email", val: "arjun@example.com" }, { label: "Phone", val: "+91 98765 43210" }].map((f, i) => (
              <div key={i}>
                <div style={{ fontSize: 12, color: "#64748B", fontWeight: 600, marginBottom: 6 }}>{f.label}</div>
                <input defaultValue={f.val} style={{ width: "100%" }} />
              </div>
            ))}
            <div>
              <div style={{ fontSize: 12, color: "#64748B", fontWeight: 600, marginBottom: 6 }}>Default Currency</div>
              <select style={{ width: "100%" }}>
                <option>INR — Indian Rupee</option>
                <option>USD — US Dollar</option>
                <option>EUR — Euro</option>
              </select>
            </div>
            <button className="gradient-btn" style={{ padding: "11px 28px", borderRadius: 10, border: "none", color: "white", fontSize: 14, fontWeight: 700, cursor: "pointer", alignSelf: "flex-start" }}>Save Changes</button>
          </div>
        </div>
      </div>
    </div>
  );

  const renderPage = () => {
    switch (activePage) {
      case "portfolio": return renderPortfolio();
      case "agents": return renderAgents();
      case "news": return renderNews();
      case "screener": return renderScreener();
      case "risk": return renderRisk();
      case "alerts": return renderAlerts();
      case "settings": return renderSettings();
      case "watchlist": return (
        <div className="fade-in" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <h2 style={{ fontSize: 20, fontWeight: 800 }}>👁 Watchlist</h2>
          <div className="glass-card" style={{ padding: 24 }}>{renderDashboard().props.children[5].props.children[0]}</div>
        </div>
      );
      case "recommendations": return (
        <div className="fade-in" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <h2 style={{ fontSize: 20, fontWeight: 800 }}>🎯 AI Recommendations</h2>
          {renderDashboard().props.children[3].props.children[0]}
        </div>
      );
      default: return renderDashboard();
    }
  };

  return (
    <>
      <style>{css}</style>
      <div style={{ display: "flex", minHeight: "100vh", background: "#0B1220" }}>

        {/* Sidebar */}
        <div className="sidebar-desktop" style={{ width: sidebarOpen ? 220 : 64, background: "#0D1526", borderRight: "1px solid rgba(255,255,255,0.06)", display: "flex", flexDirection: "column", padding: "20px 12px", position: "fixed", top: 0, left: 0, height: "100vh", zIndex: 100, transition: "width 0.3s cubic-bezier(0.4,0,0.2,1)", overflow: "hidden" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 28, paddingLeft: 4, overflow: "hidden" }}>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: "linear-gradient(135deg, #2563EB, #8B5CF6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18, flexShrink: 0 }}>⚡</div>
            {sidebarOpen && <div>
              <div style={{ fontWeight: 900, fontSize: 14, lineHeight: 1.2, whiteSpace: "nowrap" }}>QuantAI</div>
              <div style={{ fontSize: 9, color: "#64748B", fontWeight: 600, textTransform: "uppercase", letterSpacing: 1 }}>Investment Platform</div>
            </div>}
          </div>
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 3 }}>
            {navItems.map(item => (
              <div key={item.id} className={`sidebar-item ${activePage === item.id ? "active" : ""}`} onClick={() => setActivePage(item.id)}
                style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 12px", overflow: "hidden" }}>
                <span style={{ fontSize: 16, flexShrink: 0 }}>{item.icon}</span>
                {sidebarOpen && <span style={{ fontSize: 13, fontWeight: activePage === item.id ? 700 : 500, color: activePage === item.id ? "#60A5FA" : "#94A3B8", whiteSpace: "nowrap" }}>{item.label}</span>}
              </div>
            ))}
          </div>
          <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: 12, marginTop: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 12px" }}>
              <div style={{ width: 32, height: 32, borderRadius: "50%", background: "linear-gradient(135deg, #2563EB, #8B5CF6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, fontWeight: 800, flexShrink: 0 }}>A</div>
              {sidebarOpen && <div style={{ overflow: "hidden" }}>
                <div style={{ fontSize: 12, fontWeight: 700, whiteSpace: "nowrap" }}>Arjun Sharma</div>
                <div style={{ fontSize: 10, color: "#64748B" }}>Pro Plan</div>
              </div>}
            </div>
          </div>
        </div>

        {/* Main */}
        <div style={{ flex: 1, marginLeft: sidebarOpen ? 220 : 64, display: "flex", flexDirection: "column", transition: "margin-left 0.3s" }}>
          {/* Top Nav */}
          <div style={{ height: 60, background: "#0D1526", borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", alignItems: "center", padding: "0 24px", gap: 16, position: "sticky", top: 0, zIndex: 90 }}>
            <button onClick={() => setSidebarOpen(!sidebarOpen)} style={{ width: 32, height: 32, borderRadius: 8, border: "1px solid rgba(255,255,255,0.1)", background: "transparent", color: "#94A3B8", cursor: "pointer", fontSize: 16, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>☰</button>
            <div style={{ flex: 1, maxWidth: 360, position: "relative" }}>
              <span style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#64748B", fontSize: 14 }}>🔍</span>
              <input placeholder="Search stocks, ETFs, funds…" style={{ width: "100%", paddingLeft: 36 }} />
            </div>
            <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ position: "relative" }}>
                <button style={{ width: 36, height: 36, borderRadius: 9, border: "1px solid rgba(255,255,255,0.1)", background: "transparent", color: "#94A3B8", cursor: "pointer", fontSize: 17 }}>🔔</button>
                <div style={{ position: "absolute", top: -3, right: -3, width: 16, height: 16, borderRadius: "50%", background: "#EF4444", fontSize: 10, fontWeight: 800, display: "flex", alignItems: "center", justifyContent: "center", color: "white" }}>3</div>
              </div>
              <button className="gradient-btn" onClick={() => setChatOpen(true)} style={{ display: "flex", alignItems: "center", gap: 7, padding: "7px 16px", borderRadius: 9, border: "none", color: "white", fontSize: 13, fontWeight: 700, cursor: "pointer" }}>
                <span>🤖</span> Ask AI
              </button>
              <div style={{ width: 34, height: 34, borderRadius: "50%", background: "linear-gradient(135deg, #2563EB, #8B5CF6)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, cursor: "pointer" }}>A</div>
            </div>
          </div>

          {/* Content */}
          <div style={{ flex: 1, padding: "24px 28px", overflowY: "auto" }}>
            {renderPage()}
          </div>
        </div>

        {/* AI Chat */}
        {chatOpen && (
          <div style={{ position: "fixed", bottom: 24, right: 24, width: 380, height: 520, zIndex: 200, display: "flex", flexDirection: "column", borderRadius: 20, overflow: "hidden", boxShadow: "0 24px 80px rgba(0,0,0,0.6)", border: "1px solid rgba(255,255,255,0.1)", background: "#111827" }}>
            <div style={{ padding: "16px 20px", background: "linear-gradient(135deg, #1E3A5F, #1a237e)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{ width: 36, height: 36, borderRadius: "50%", background: "linear-gradient(135deg, #2563EB, #8B5CF6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>🤖</div>
                <div>
                  <div style={{ fontWeight: 800, fontSize: 14 }}>AI Investment Strategist</div>
                  <div style={{ fontSize: 11, color: "#22C55E", display: "flex", alignItems: "center", gap: 4 }}>
                    <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#22C55E" }} className="pulse" /> Online
                  </div>
                </div>
              </div>
              <button onClick={() => setChatOpen(false)} style={{ background: "rgba(255,255,255,0.1)", border: "none", borderRadius: "50%", width: 28, height: 28, cursor: "pointer", color: "white", fontSize: 16 }}>×</button>
            </div>
            <div style={{ flex: 1, overflowY: "auto", padding: "16px 16px 8px" }}>
              {messages.map((m, i) => (
                <div key={i} style={{ marginBottom: 14, display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}>
                  {m.role === "ai" && <div style={{ width: 28, height: 28, borderRadius: "50%", background: "linear-gradient(135deg, #2563EB, #8B5CF6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, marginRight: 8, flexShrink: 0, marginTop: 2 }}>🤖</div>}
                  <div style={{ maxWidth: "80%", padding: "10px 14px", borderRadius: m.role === "user" ? "14px 14px 4px 14px" : "14px 14px 14px 4px", background: m.role === "user" ? "linear-gradient(135deg, #2563EB, #1D4ED8)" : "rgba(255,255,255,0.07)", fontSize: 13, lineHeight: 1.6, color: "#E2E8F0" }}>
                    {m.text}
                  </div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>
            <div style={{ padding: "10px 14px", borderTop: "1px solid rgba(255,255,255,0.06)", display: "flex", gap: 8 }}>
              <input value={chatInput} onChange={e => setChatInput(e.target.value)} onKeyDown={e => e.key === "Enter" && sendMessage()}
                placeholder="Ask about stocks, markets…" style={{ flex: 1, padding: "9px 14px", borderRadius: 10 }} />
              <button className="gradient-btn" onClick={sendMessage} style={{ padding: "9px 16px", borderRadius: 10, border: "none", color: "white", cursor: "pointer", fontSize: 18 }}>↑</button>
            </div>
          </div>
        )}

        {/* Floating Chat Button */}
        {!chatOpen && (
          <button onClick={() => setChatOpen(true)} className="gradient-btn float" style={{ position: "fixed", bottom: 28, right: 28, width: 56, height: 56, borderRadius: "50%", border: "none", cursor: "pointer", fontSize: 24, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 8px 32px rgba(37,99,235,0.5)", zIndex: 150 }}>
            🤖
          </button>
        )}
      </div>
    </>
  );
}
