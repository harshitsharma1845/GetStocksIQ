from datetime import datetime, timezone

class ScoringEngine:
    """Multi-Factor Quantitative Stock Scoring Engine combining 7 independent financial pillars:
    - Fundamentals (25%): Profitability, Business Growth, Solvency, Cash Generation
    - Technicals (20%): Moving Average Alignments, RSI Oscillator, MACD, Bollinger Bands
    - Valuation (15%): P/E, Forward P/E, PEG, P/B, P/S, EV/EBITDA, Dividend Yield
    - Momentum (15%): Multi-timeframe Returns (1M, 3M, 6M), 52-Week Range Position, Relative Volume
    - Sentiment (10%): Verified News Sentiment
    - Risk (10%): Inverted (100 = Lowest Risk / Safest) — Volatility, Drawdown, ATR %, Beta, Leverage
    - Liquidity (5%): Daily Rupee Turnover, Market Capitalization
    """

    # Recommendation Thresholds
    STRONG_BUY_THRESHOLD = 80
    BUY_THRESHOLD = 65
    HOLD_THRESHOLD = 50
    REDUCE_THRESHOLD = 35

    DEFAULT_WEIGHTS = {
        "fundamentals": 0.25,
        "technicals": 0.20,
        "valuation": 0.15,
        "momentum": 0.15,
        "sentiment": 0.10,
        "risk": 0.10,
        "liquidity": 0.05,
    }

    @classmethod
    def evaluate_stock(cls, fundamentals_data, technicals_data, news_sentiment_score=50, weights=None):
        w = weights or cls.DEFAULT_WEIGHTS
        fundamentals = fundamentals_data if isinstance(fundamentals_data, dict) else {}
        technicals = technicals_data if isinstance(technicals_data, dict) else {}

        # 1. Fundamental Score (0–100) — Profitability, Growth, Solvency, Cash Generation
        if fundamentals.get("available"):
            fundamental_score = fundamentals.get("fundamental_score", 50)
        else:
            fundamental_score = 50

        # 2. Technical Score (0–100) — MA Alignment, RSI Setup, MACD, Bollinger
        if technicals.get("available"):
            technical_score = technicals.get("technical_score", 50)
        else:
            technical_score = 50

        # 3. Valuation Score (0–100) — Multi-multiples (P/E, Forward P/E, PEG, P/B, P/S, EV/EBITDA, Yield)
        valuation_score, val_details = cls._compute_valuation_score(fundamentals)

        # 4. Momentum Score (0–100) — 1M, 3M, 6M returns, 52W positioning, relative volume
        momentum_score, mom_details = cls._compute_momentum_score(technicals)

        # 5. News Sentiment Score (0–100)
        try:
            sentiment_score = max(0, min(100, int(news_sentiment_score)))
        except (ValueError, TypeError):
            sentiment_score = 50

        # 6. Risk Score (0–100: Higher score = lower risk / more resilient)
        risk_score, risk_label, risk_details = cls._compute_risk_score(technicals, fundamentals)

        # 7. Liquidity Score (0–100) — Turnover & Market Cap
        liquidity_score, liq_details = cls._compute_liquidity_score(technicals, fundamentals)

        # Weighted Composite Score
        composite = (
            (fundamental_score * w["fundamentals"]) +
            (technical_score * w["technicals"]) +
            (valuation_score * w["valuation"]) +
            (momentum_score * w["momentum"]) +
            (sentiment_score * w["sentiment"]) +
            (risk_score * w["risk"]) +
            (liquidity_score * w["liquidity"])
        )
        overall_score = int(round(max(5, min(98, composite))))

        # Deterministic Signal Classification based on Configurable Thresholds
        if overall_score >= cls.STRONG_BUY_THRESHOLD:
            signal = "Strong Buy"
            summary = "Constructive multi-factor quantitative profile with solid fundamentals, favorable technical structure, and supportive momentum."
        elif overall_score >= cls.BUY_THRESHOLD:
            signal = "Buy"
            summary = "Constructive setup with positive fundamental metrics and supportive technical alignment."
        elif overall_score >= cls.HOLD_THRESHOLD:
            signal = "Hold"
            summary = "Neutral risk/reward balance across key fundamental and technical metrics."
        elif overall_score >= cls.REDUCE_THRESHOLD:
            signal = "Reduce"
            summary = "Elevated valuation multiples, deteriorating momentum, or higher risk profile suggest caution."
        else:
            signal = "Avoid"
            summary = "Adverse technical indicators, high volatility, or weak fundamental ratios."

        factor_scores = {
            "fundamentals": fundamental_score,
            "technicals": technical_score,
            "valuation": valuation_score,
            "momentum": momentum_score,
            "sentiment": sentiment_score,
            "risk": risk_score,
            "liquidity": liquidity_score,
        }

        # Data Quality & Confidence Calculation
        confidence, data_quality_pct, missing_metrics = cls._calculate_confidence_and_completeness(
            fundamentals, technicals, news_sentiment_score, overall_score
        )

        # Dynamic Attribution (Strengths & Risks)
        strengths, risks = cls._extract_strengths_and_risks(
            fundamentals, technicals, factor_scores, risk_label
        )

        factor_details = {
            "valuation": val_details,
            "momentum": mom_details,
            "risk": risk_details,
            "liquidity": liq_details,
        }

        return {
            "overall_score": overall_score,
            "signal": signal,
            "confidence": confidence,
            "data_quality": data_quality_pct,
            "missing_metrics": missing_metrics,
            "risk_label": risk_label,
            "summary": summary,
            "factor_scores": factor_scores,
            "factor_details": factor_details,
            "weights": w,
            "strengths": strengths,
            "risks": risks,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    # =========================================================================
    # 3. VALUATION PILLAR (15%)
    # Multiples: Trailing P/E, Forward P/E, PEG, P/B, P/S, EV/EBITDA, Dividend Yield
    # (Note: Growth is not double-counted separately here since PEG already embeds growth)
    # =========================================================================
    @staticmethod
    def _compute_valuation_score(fundamentals):
        if not fundamentals or not fundamentals.get("available"):
            return 50, {"evaluated": False, "reason": "No fundamental data available"}

        raw = fundamentals.get("raw_metrics", {})
        pe = raw.get("pe")
        forward_pe = raw.get("forward_pe")
        peg = raw.get("peg_ratio")
        pb = raw.get("pb")
        ps = raw.get("ps")
        ev_ebitda = raw.get("ev_to_ebitda")
        div_yield = raw.get("dividend_yield")

        scores = []
        weights = []
        details = {}

        # A. Trailing P/E & Forward P/E (Weight: 0.35)
        pe_sub = []
        if pe is not None:
            if pe <= 0:
                pe_sub.append(20.0) # Unprofitable / negative earnings
                details["pe_status"] = "Negative Earnings"
            elif pe <= 15.0:
                pe_sub.append(90.0)
            elif pe <= 28.0:
                pe_sub.append(85.0 - ((pe - 15.0) / 13.0) * 20.0)
            elif pe <= 55.0:
                pe_sub.append(65.0 - ((pe - 28.0) / 27.0) * 25.0)
            elif pe <= 90.0:
                pe_sub.append(40.0 - ((pe - 55.0) / 35.0) * 20.0)
            else:
                pe_sub.append(15.0)

        if forward_pe is not None and forward_pe > 0:
            if forward_pe <= 14.0:
                pe_sub.append(90.0)
            elif forward_pe <= 25.0:
                pe_sub.append(85.0 - ((forward_pe - 14.0) / 11.0) * 20.0)
            elif forward_pe <= 50.0:
                pe_sub.append(65.0 - ((forward_pe - 25.0) / 25.0) * 25.0)
            else:
                pe_sub.append(25.0)

        if pe_sub:
            scores.append(sum(pe_sub) / len(pe_sub))
            weights.append(0.35)

        # B. PEG Ratio (Weight: 0.20) — Growth-adjusted valuation
        if peg is not None and peg > 0:
            if peg <= 0.9:
                scores.append(95.0) # Significantly undervalued relative to growth
            elif peg <= 1.5:
                scores.append(85.0 - ((peg - 0.9) / 0.6) * 15.0)
            elif peg <= 2.5:
                scores.append(70.0 - ((peg - 1.5) / 1.0) * 25.0)
            elif peg <= 4.0:
                scores.append(45.0 - ((peg - 2.5) / 1.5) * 20.0)
            else:
                scores.append(20.0)
            weights.append(0.20)

        # C. Price to Book (P/B) (Weight: 0.15)
        if pb is not None and pb > 0:
            if pb <= 1.5:
                scores.append(90.0)
            elif pb <= 3.5:
                scores.append(80.0 - ((pb - 1.5) / 2.0) * 20.0)
            elif pb <= 8.0:
                scores.append(60.0 - ((pb - 3.5) / 4.5) * 25.0)
            else:
                scores.append(25.0)
            weights.append(0.15)

        # D. Price to Sales (P/S) (Weight: 0.15)
        if ps is not None and ps > 0:
            if ps <= 1.5:
                scores.append(85.0)
            elif ps <= 4.0:
                scores.append(75.0 - ((ps - 1.5) / 2.5) * 20.0)
            elif ps <= 10.0:
                scores.append(55.0 - ((ps - 4.0) / 6.0) * 25.0)
            else:
                scores.append(25.0)
            weights.append(0.15)

        # E. EV / EBITDA (Weight: 0.15)
        if ev_ebitda is not None and ev_ebitda > 0:
            if ev_ebitda <= 10.0:
                scores.append(90.0)
            elif ev_ebitda <= 18.0:
                scores.append(80.0 - ((ev_ebitda - 10.0) / 8.0) * 20.0)
            elif ev_ebitda <= 30.0:
                scores.append(60.0 - ((ev_ebitda - 18.0) / 12.0) * 25.0)
            else:
                scores.append(25.0)
            weights.append(0.15)

        # Dividend Yield bonus / contribution
        if div_yield is not None and div_yield > 0.015:
            bonus = min(8.0, (div_yield - 0.015) * 150.0)
            details["dividend_bonus"] = round(bonus, 1)
        else:
            bonus = 0.0

        if scores and sum(weights) > 0:
            norm_w = [w / sum(weights) for w in weights]
            raw_val_score = sum(s * w for s, w in zip(scores, norm_w)) + bonus
            val_score = int(round(max(10, min(95, raw_val_score))))
        else:
            val_score = 50

        details["valuation_score"] = val_score
        return val_score, details

    # =========================================================================
    # 4. MOMENTUM PILLAR (15%)
    # Multi-timeframe Returns (1M, 3M, 6M), 52-Week Range Position, Relative Volume
    # (Note: Decoupled from Technical Moving Averages / RSI to avoid double-counting)
    # =========================================================================
    @staticmethod
    def _compute_momentum_score(technicals):
        if not technicals or not technicals.get("available"):
            return 50, {"evaluated": False, "reason": "No technical/price history available"}

        mom_data = technicals.get("momentum_metrics", {})
        ret_1m = mom_data.get("return_1m")
        ret_3m = mom_data.get("return_3m")
        ret_6m = mom_data.get("return_6m")
        range_pos = mom_data.get("range_position_52w", 50.0)
        rel_vol = mom_data.get("relative_volume", 1.0)

        scores = []
        weights = []
        details = {}

        # A. 1-Month Return (Weight: 0.25)
        if ret_1m is not None:
            if ret_1m < -12.0:
                scores.append(20.0)
            elif ret_1m < 0:
                scores.append(40.0 + ((ret_1m + 12.0) / 12.0) * 15.0)
            elif ret_1m <= 10.0:
                scores.append(60.0 + (ret_1m / 10.0) * 25.0)
            else:
                scores.append(min(98.0, 85.0 + (ret_1m - 10.0) * 0.8))
            weights.append(0.25)

        # B. 3-Month Return (Weight: 0.25)
        if ret_3m is not None:
            if ret_3m < -18.0:
                scores.append(15.0)
            elif ret_3m < 0:
                scores.append(35.0 + ((ret_3m + 18.0) / 18.0) * 20.0)
            elif ret_3m <= 20.0:
                scores.append(60.0 + (ret_3m / 20.0) * 25.0)
            else:
                scores.append(min(98.0, 85.0 + (ret_3m - 20.0) * 0.6))
            weights.append(0.25)

        # C. 6-Month Return (Weight: 0.20)
        if ret_6m is not None:
            if ret_6m < -25.0:
                scores.append(15.0)
            elif ret_6m < 0:
                scores.append(35.0 + ((ret_6m + 25.0) / 25.0) * 20.0)
            elif ret_6m <= 35.0:
                scores.append(60.0 + (ret_6m / 35.0) * 25.0)
            else:
                scores.append(min(98.0, 85.0 + (ret_6m - 35.0) * 0.4))
            weights.append(0.20)

        # D. 52-Week Range Positioning (Weight: 0.15) — Relative strength position
        if range_pos is not None:
            if range_pos >= 75.0:
                scores.append(85.0) # Near annual highs
            elif range_pos >= 45.0:
                scores.append(65.0 + ((range_pos - 45.0) / 30.0) * 20.0)
            elif range_pos >= 20.0:
                scores.append(40.0 + ((range_pos - 20.0) / 25.0) * 20.0)
            else:
                scores.append(25.0) # Near annual lows
            weights.append(0.15)

        # E. Relative Volume Trend (Weight: 0.15)
        if rel_vol is not None:
            if rel_vol >= 1.4:
                scores.append(85.0) # Volume expansion supporting trend
            elif rel_vol >= 0.85:
                scores.append(65.0) # Stable volume
            else:
                scores.append(45.0) # Fading interest
            weights.append(0.15)

        if scores and sum(weights) > 0:
            norm_w = [w / sum(weights) for w in weights]
            raw_mom = sum(s * w for s, w in zip(scores, norm_w))
            mom_score = int(round(max(10, min(95, raw_mom))))
        else:
            mom_score = 50

        details["momentum_score"] = mom_score
        return mom_score, details

    # =========================================================================
    # 6. RISK PILLAR (10%) — Inverted Scale (Higher = Lower Risk / More Stable)
    # Volatility, Maximum Drawdown, ATR %, Beta, Financial Leverage
    # =========================================================================
    @staticmethod
    def _compute_risk_score(technicals, fundamentals):
        if not technicals or not technicals.get("available"):
            return 50, "Moderate Risk", {"evaluated": False}

        risk_metrics = technicals.get("risk_metrics", {})
        ann_vol = risk_metrics.get("annualized_volatility")
        max_dd = risk_metrics.get("max_drawdown")
        atr_pct = risk_metrics.get("atr_pct", 2.5)

        raw_fund = fundamentals.get("raw_metrics", {}) if fundamentals else {}
        beta = raw_fund.get("beta")
        debt_to_equity = raw_fund.get("debt_to_equity")
        is_financial = raw_fund.get("is_financial", False)

        scores = []
        weights = []
        details = {}

        # A. Annualized Volatility (Weight: 0.30)
        if ann_vol is not None:
            if ann_vol <= 18.0:
                scores.append(90.0) # Very low volatility
            elif ann_vol <= 30.0:
                scores.append(85.0 - ((ann_vol - 18.0) / 12.0) * 20.0)
            elif ann_vol <= 48.0:
                scores.append(65.0 - ((ann_vol - 30.0) / 18.0) * 30.0)
            else:
                scores.append(max(15.0, 35.0 - ((ann_vol - 48.0) / 20.0) * 15.0))
            weights.append(0.30)

        # B. Maximum Drawdown (Weight: 0.25)
        if max_dd is not None:
            if max_dd <= 12.0:
                scores.append(90.0) # Highly resilient
            elif max_dd <= 25.0:
                scores.append(80.0 - ((max_dd - 12.0) / 13.0) * 20.0)
            elif max_dd <= 45.0:
                scores.append(60.0 - ((max_dd - 25.0) / 20.0) * 25.0)
            else:
                scores.append(max(15.0, 35.0 - ((max_dd - 45.0) / 25.0) * 20.0))
            weights.append(0.25)

        # C. Daily ATR % Volatility (Weight: 0.15)
        if atr_pct is not None:
            if atr_pct <= 1.8:
                scores.append(90.0)
            elif atr_pct <= 3.2:
                scores.append(70.0 - ((atr_pct - 1.8) / 1.4) * 25.0)
            else:
                scores.append(max(20.0, 45.0 - ((atr_pct - 3.2) / 2.0) * 20.0))
            weights.append(0.15)

        # D. Market Beta (Weight: 0.15) — If available (excluded if missing, not set to 0)
        if beta is not None and beta > 0:
            if 0.6 <= beta <= 1.1:
                scores.append(85.0) # Balanced market pace
            elif 1.1 < beta <= 1.5:
                scores.append(65.0)
            elif beta > 1.5:
                scores.append(35.0) # High systemic risk
            else: # beta < 0.6
                scores.append(80.0)
            weights.append(0.15)

        # E. Solvency / Leverage Risk (Weight: 0.15) — Default distress check
        if debt_to_equity is not None:
            if is_financial:
                scores.append(75.0 if debt_to_equity < 600 else 55.0)
            else:
                if debt_to_equity < 40.0:
                    scores.append(90.0) # Negligible leverage risk
                elif debt_to_equity <= 120.0:
                    scores.append(70.0)
                elif debt_to_equity <= 220.0:
                    scores.append(45.0)
                else:
                    scores.append(25.0) # High financial distress risk
            weights.append(0.15)

        if scores and sum(weights) > 0:
            norm_w = [w / sum(weights) for w in weights]
            raw_risk = sum(s * w for s, w in zip(scores, norm_w))
            risk_score = int(round(max(10, min(95, raw_risk))))
        else:
            risk_score = 50

        if risk_score >= 70:
            risk_label = "Low Risk"
        elif risk_score <= 45:
            risk_label = "High Risk"
        else:
            risk_label = "Moderate Risk"

        details["risk_score"] = risk_score
        details["risk_label"] = risk_label
        return risk_score, risk_label, details

    # =========================================================================
    # 7. LIQUIDITY PILLAR (5%)
    # Daily Rupee Turnover & Market Capitalization
    # =========================================================================
    @staticmethod
    def _compute_liquidity_score(technicals, fundamentals):
        price = technicals.get("latest_price", 0) if technicals else 0
        mom = technicals.get("momentum_metrics", {}) if technicals else {}
        avg_vol = mom.get("avg_vol_30d", 0)
        raw = fundamentals.get("raw_metrics", {}) if fundamentals else {}
        mcap = raw.get("market_cap")

        scores = []
        weights = []

        # A. Rupee Turnover (Weight: 0.65)
        if avg_vol > 0 and price > 0:
            turnover_daily = avg_vol * price
            if turnover_daily >= 250_000_000: # >= ₹25 Cr
                scores.append(95.0)
            elif turnover_daily >= 50_000_000: # >= ₹5 Cr
                scores.append(80.0)
            elif turnover_daily >= 10_000_000: # >= ₹1 Cr
                scores.append(65.0)
            elif turnover_daily >= 2_500_000:  # >= ₹25 L
                scores.append(50.0)
            else:
                scores.append(30.0)
            weights.append(0.65)

        # B. Market Cap Tier (Weight: 0.35)
        if mcap is not None and mcap > 0:
            if mcap >= 200_000_000_000: # >= ₹20,000 Cr (Large Cap)
                scores.append(90.0)
            elif mcap >= 50_000_000_000: # >= ₹5,000 Cr (Mid Cap)
                scores.append(75.0)
            elif mcap >= 10_000_000_000: # >= ₹1,000 Cr (Small Cap)
                scores.append(60.0)
            else:
                scores.append(40.0)
            weights.append(0.35)

        if scores and sum(weights) > 0:
            norm_w = [w / sum(weights) for w in weights]
            liq_score = int(round(max(15, min(95, sum(s * w for s, w in zip(scores, norm_w))))))
        else:
            liq_score = 65 if price > 50 else 50

        return liq_score, {"liquidity_score": liq_score}

    # =========================================================================
    # DATA QUALITY & CONFIDENCE
    # =========================================================================
    @staticmethod
    def _calculate_confidence_and_completeness(fundamentals, technicals, sentiment, overall_score):
        total_possible = 10
        available_count = 0
        missing = []

        if fundamentals.get("available"):
            raw = fundamentals.get("raw_metrics", {})
            for key in ["roe", "revenue_growth", "debt_to_equity", "free_cash_flow", "pe"]:
                if raw.get(key) is not None:
                    available_count += 1
                else:
                    missing.append(key)
        else:
            missing.extend(["fundamentals_data", "roe", "revenue_growth", "debt_to_equity", "pe"])

        if technicals.get("available"):
            available_count += 3 # MA, RSI, MACD
            mom = technicals.get("momentum_metrics", {})
            if mom.get("return_1m") is not None:
                available_count += 1
            else:
                missing.append("return_1m")
            if technicals.get("risk_metrics", {}).get("annualized_volatility") is not None:
                available_count += 1
            else:
                missing.append("annualized_volatility")
        else:
            missing.extend(["technicals_data", "moving_averages", "rsi_14", "momentum_data"])

        completeness_pct = int(round((available_count / total_possible) * 100))
        # Confidence blends data completeness with signal divergence
        confidence = int(round(max(35, min(95, (completeness_pct * 0.65) + (abs(overall_score - 50) * 0.45)))))

        return confidence, completeness_pct, missing

    # =========================================================================
    # STRENGTHS & RISKS EXPLAINABILITY
    # =========================================================================
    @staticmethod
    def _extract_strengths_and_risks(fundamentals, technicals, factor_scores, risk_label):
        strengths = []
        risks = []

        if fundamentals.get("available"):
            raw = fundamentals.get("raw_metrics", {})
            roe = raw.get("roe")
            if roe is not None:
                if roe > 0.18:
                    strengths.append(f"Strong Return on Equity ({roe * 100:.1f}%)")
                elif roe < 0.06:
                    risks.append(f"Subdued Return on Equity ({roe * 100:.1f}%)")

            rev_g = raw.get("revenue_growth")
            if rev_g is not None:
                if rev_g > 0.12:
                    strengths.append(f"Robust Top-Line Revenue Growth ({rev_g * 100:.1f}%)")
                elif rev_g < -0.05:
                    risks.append(f"Declining Revenue Growth ({rev_g * 100:.1f}%)")

            de = raw.get("debt_to_equity")
            if de is not None and not raw.get("is_financial"):
                if de < 35:
                    strengths.append("Conservative balance sheet with low financial leverage")
                elif de > 160:
                    risks.append(f"Elevated Debt-to-Equity ratio ({de:.1f})")

            fcf = raw.get("free_cash_flow")
            if fcf is not None and fcf > 0:
                strengths.append("Positive Free Cash Flow generation")

        if technicals.get("available"):
            rsi = technicals.get("rsi_14", 50)
            if 50 <= rsi <= 68:
                strengths.append(f"Healthy bullish oscillator momentum (RSI {rsi})")
            elif rsi > 75:
                risks.append(f"Technical momentum overbought (RSI {rsi})")
            elif rsi < 32:
                risks.append(f"Weak downward price pressure (RSI {rsi})")

            trend = technicals.get("trend_signal")
            if trend == "Bullish":
                strengths.append("Constructive price trend above major moving averages")
            elif trend == "Bearish":
                risks.append("Trading below major moving average resistance levels")

        val_score = factor_scores.get("valuation", 50)
        if val_score >= 70:
            strengths.append("Attractive valuation multiples relative to financial output")
        elif val_score <= 35:
            risks.append("Premium valuation pricing in ambitious expectations")

        mom_score = factor_scores.get("momentum", 50)
        if mom_score >= 75:
            strengths.append("Outperforming price momentum across recent trading sessions")
        elif mom_score <= 35:
            risks.append("Lagging multi-timeframe price momentum")

        if risk_label == "High Risk":
            risks.append("Elevated historical price volatility or deep drawdown")
        elif risk_label == "Low Risk":
            strengths.append("Low historical price volatility and resilient drawdown profile")

        if not strengths:
            strengths.append("Established market liquidity and ongoing trading interest")
        if not risks:
            risks.append("Broad market volatility and sector rotation risk")

        return strengths[:4], risks[:4]

