class FundamentalService:
    """Extracts, validates and scores fundamental financial metrics.
    Focuses purely on Profitability, Business Growth, Financial Health/Solvency, and Cash Generation.
    Eliminates valuation multiple overlaps to keep pillars conceptually independent.
    """

    @staticmethod
    def extract_fundamentals(info_dict):
        if not info_dict or not isinstance(info_dict, dict):
            return {
                "available": False,
                "reason": "Fundamental data is not available"
            }

        try:
            info = info_dict

            def safe_float(val, default=None):
                if val is None:
                    return default
                try:
                    v = float(val)
                    if v != v or v == float('inf') or v == float('-inf'):
                        return default
                    return v
                except (ValueError, TypeError):
                    return default

            def safe_pct(val):
                f = safe_float(val)
                if f is None:
                    return "Not available"
                return f"{f * 100:.2f}%"

            def safe_currency(val):
                f = safe_float(val)
                if f is None:
                    return "Not available"
                if abs(f) >= 1_000_000_000_000:
                    return f"₹{f / 1_000_000_000_000:.2f} T"
                if abs(f) >= 1_000_000_000:
                    return f"₹{f / 1_000_000_000:.2f} B"
                if abs(f) >= 10_000_000:
                    return f"₹{f / 10_000_000:.2f} Cr"
                if abs(f) >= 100_000:
                    return f"₹{f / 100_000:.2f} L"
                return f"₹{f:,.2f}"

            # 1. Profitability & Returns
            roe = safe_float(info.get("returnOnEquity"))
            roa = safe_float(info.get("returnOnAssets"))
            profit_margin = safe_float(info.get("profitMargins"))
            operating_margin = safe_float(info.get("operatingMargins"))
            gross_margin = safe_float(info.get("grossMargins"))

            # 2. Growth Dynamics
            revenue_growth = safe_float(info.get("revenueGrowth"))
            earnings_growth = safe_float(info.get("earningsGrowth"))
            quarterly_earnings_growth = safe_float(info.get("earningsQuarterlyGrowth"))

            # 3. Balance Sheet & Solvency
            debt_to_equity = safe_float(info.get("debtToEquity"))
            current_ratio = safe_float(info.get("currentRatio"))
            quick_ratio = safe_float(info.get("quickRatio"))
            total_debt = safe_float(info.get("totalDebt"))
            total_cash = safe_float(info.get("totalCash"))

            # 4. Cash Generation & Scale
            free_cash_flow = safe_float(info.get("freeCashflow"))
            operating_cash_flow = safe_float(info.get("operatingCashflow"))
            ebitda = safe_float(info.get("ebitda"))
            total_revenue = safe_float(info.get("totalRevenue"))
            market_cap = safe_float(info.get("marketCap"))
            eps = safe_float(info.get("trailingEps") or info.get("forwardEps"))
            beta = safe_float(info.get("beta"))

            # 5. Valuation Multiples (extracted cleanly for the separate Valuation Pillar)
            pe = safe_float(info.get("trailingPE"))
            forward_pe = safe_float(info.get("forwardPE"))
            peg_ratio = safe_float(info.get("pegRatio") or info.get("trailingPegRatio"))
            pb = safe_float(info.get("priceToBook"))
            ps = safe_float(info.get("priceToSalesTrailing12Months"))
            ev_to_ebitda = safe_float(info.get("enterpriseToEbitda"))
            dividend_yield = safe_float(info.get("dividendYield"))

            sector = info.get("sector", "Not available")
            industry = info.get("industry", "Not available")
            is_financial = "Financial" in str(sector) or "Bank" in str(industry) or "NBFC" in str(industry)

            # ==============================================================
            # DETERMINISTIC FUNDAMENTAL SCORING (0–100)
            # Pillars: Profitability (35%), Growth (30%), Solvency (20%), Cash Flow (15%)
            # ==============================================================
            sub_scores = []
            sub_weights = []

            # --- A. Profitability (Weight: 0.35) ---
            prof_sub = []
            if roe is not None:
                if roe < 0:
                    prof_sub.append(15.0)
                elif roe < 0.10:
                    prof_sub.append(35.0 + (roe / 0.10) * 20.0)
                elif roe <= 0.22:
                    prof_sub.append(55.0 + ((roe - 0.10) / 0.12) * 35.0)
                else:
                    prof_sub.append(min(98.0, 90.0 + ((roe - 0.22) / 0.10) * 8.0))

            if roa is not None:
                if roa < 0:
                    prof_sub.append(15.0)
                elif roa < 0.05:
                    prof_sub.append(35.0 + (roa / 0.05) * 25.0)
                elif roa <= 0.12:
                    prof_sub.append(60.0 + ((roa - 0.05) / 0.07) * 30.0)
                else:
                    prof_sub.append(min(98.0, 90.0 + (roa - 0.12) * 50.0))

            if operating_margin is not None:
                if operating_margin < 0:
                    prof_sub.append(15.0)
                elif operating_margin < 0.08:
                    prof_sub.append(35.0 + (operating_margin / 0.08) * 25.0)
                elif operating_margin <= 0.25:
                    prof_sub.append(60.0 + ((operating_margin - 0.08) / 0.17) * 30.0)
                else:
                    prof_sub.append(min(98.0, 90.0 + ((operating_margin - 0.25) / 0.15) * 8.0))

            if profit_margin is not None:
                if profit_margin < 0:
                    prof_sub.append(15.0)
                elif profit_margin < 0.06:
                    prof_sub.append(35.0 + (profit_margin / 0.06) * 25.0)
                elif profit_margin <= 0.18:
                    prof_sub.append(60.0 + ((profit_margin - 0.06) / 0.12) * 30.0)
                else:
                    prof_sub.append(min(98.0, 90.0 + ((profit_margin - 0.18) / 0.10) * 8.0))

            if prof_sub:
                sub_scores.append(sum(prof_sub) / len(prof_sub))
                sub_weights.append(0.35)

            # --- B. Business Growth (Weight: 0.30) ---
            growth_sub = []
            if revenue_growth is not None:
                if revenue_growth < -0.15:
                    growth_sub.append(15.0)
                elif revenue_growth < 0:
                    growth_sub.append(25.0 + ((revenue_growth + 0.15) / 0.15) * 20.0)
                elif revenue_growth <= 0.18:
                    growth_sub.append(45.0 + (revenue_growth / 0.18) * 40.0)
                else:
                    growth_sub.append(min(98.0, 85.0 + ((revenue_growth - 0.18) / 0.20) * 12.0))

            if earnings_growth is not None:
                if earnings_growth < -0.20:
                    growth_sub.append(15.0)
                elif earnings_growth < 0:
                    growth_sub.append(25.0 + ((earnings_growth + 0.20) / 0.20) * 20.0)
                elif earnings_growth <= 0.25:
                    growth_sub.append(45.0 + (earnings_growth / 0.25) * 40.0)
                else:
                    growth_sub.append(min(98.0, 85.0 + ((earnings_growth - 0.25) / 0.25) * 12.0))
            elif quarterly_earnings_growth is not None:
                if quarterly_earnings_growth < -0.20:
                    growth_sub.append(15.0)
                elif quarterly_earnings_growth < 0:
                    growth_sub.append(30.0)
                elif quarterly_earnings_growth <= 0.25:
                    growth_sub.append(50.0 + (quarterly_earnings_growth / 0.25) * 35.0)
                else:
                    growth_sub.append(min(98.0, 85.0))

            if growth_sub:
                sub_scores.append(sum(growth_sub) / len(growth_sub))
                sub_weights.append(0.30)

            # --- C. Financial Health & Solvency (Weight: 0.20) ---
            solvency_sub = []
            if debt_to_equity is not None:
                if is_financial:
                    if debt_to_equity < 300:
                        solvency_sub.append(85.0)
                    elif debt_to_equity < 700:
                        solvency_sub.append(70.0)
                    else:
                        solvency_sub.append(50.0)
                else:
                    if debt_to_equity < 25.0:
                        solvency_sub.append(95.0)
                    elif debt_to_equity <= 75.0:
                        solvency_sub.append(85.0 - ((debt_to_equity - 25.0) / 50.0) * 20.0)
                    elif debt_to_equity <= 160.0:
                        solvency_sub.append(65.0 - ((debt_to_equity - 75.0) / 85.0) * 25.0)
                    else:
                        solvency_sub.append(max(15.0, 40.0 - ((debt_to_equity - 160.0) / 100.0) * 20.0))

            if current_ratio is not None and not is_financial:
                if current_ratio < 0.8:
                    solvency_sub.append(25.0)
                elif current_ratio < 1.2:
                    solvency_sub.append(45.0 + ((current_ratio - 0.8) / 0.4) * 25.0)
                elif current_ratio <= 2.5:
                    solvency_sub.append(70.0 + ((current_ratio - 1.2) / 1.3) * 25.0)
                else:
                    solvency_sub.append(85.0)

            if quick_ratio is not None and not is_financial:
                if quick_ratio < 0.6:
                    solvency_sub.append(30.0)
                elif quick_ratio < 1.0:
                    solvency_sub.append(50.0 + ((quick_ratio - 0.6) / 0.4) * 25.0)
                else:
                    solvency_sub.append(min(95.0, 75.0 + (quick_ratio - 1.0) * 15.0))

            if solvency_sub:
                sub_scores.append(sum(solvency_sub) / len(solvency_sub))
                sub_weights.append(0.20)

            # --- D. Cash Generation & Quality (Weight: 0.15) ---
            cash_sub = []
            if free_cash_flow is not None:
                if free_cash_flow > 0:
                    if total_revenue and total_revenue > 0:
                        fcf_margin = free_cash_flow / total_revenue
                        if fcf_margin > 0.15:
                            cash_sub.append(95.0)
                        elif fcf_margin > 0.05:
                            cash_sub.append(75.0)
                        else:
                            cash_sub.append(60.0)
                    else:
                        cash_sub.append(75.0)
                else:
                    cash_sub.append(25.0)

            if operating_cash_flow is not None:
                if operating_cash_flow > 0:
                    cash_sub.append(80.0)
                else:
                    cash_sub.append(20.0)

            if cash_sub:
                sub_scores.append(sum(cash_sub) / len(cash_sub))
                sub_weights.append(0.15)

            # Dynamically normalize weights across available fundamental sub-factors
            if sub_scores and sum(sub_weights) > 0:
                normalized_weights = [w / sum(sub_weights) for w in sub_weights]
                weighted_fund_score = sum(s * w for s, w in zip(sub_scores, normalized_weights))
                fundamental_score = int(round(max(10, min(95, weighted_fund_score))))
            else:
                fundamental_score = 50

            return {
                "available": True,
                "pe_ratio": f"{pe:.2f}" if pe is not None else "Not available",
                "pb_ratio": f"{pb:.2f}" if pb is not None else "Not available",
                "roe": safe_pct(roe),
                "roa": safe_pct(roa),
                "debt_to_equity": f"{debt_to_equity:.2f}" if debt_to_equity is not None else "Not available",
                "profit_margin": safe_pct(profit_margin),
                "operating_margin": safe_pct(operating_margin),
                "gross_margin": safe_pct(gross_margin),
                "revenue_growth": safe_pct(revenue_growth),
                "earnings_growth": safe_pct(earnings_growth),
                "dividend_yield": safe_pct(dividend_yield),
                "current_ratio": f"{current_ratio:.2f}" if current_ratio is not None else "Not available",
                "quick_ratio": f"{quick_ratio:.2f}" if quick_ratio is not None else "Not available",
                "free_cash_flow": safe_currency(free_cash_flow),
                "operating_cash_flow": safe_currency(operating_cash_flow),
                "ebitda": safe_currency(ebitda),
                "total_revenue": safe_currency(total_revenue),
                "market_cap": safe_currency(market_cap),
                "eps": f"₹{eps:.2f}" if eps is not None else "Not available",
                "sector": sector,
                "industry": industry,
                "fundamental_score": fundamental_score,
                "raw_metrics": {
                    "pe": pe,
                    "forward_pe": forward_pe,
                    "peg_ratio": peg_ratio,
                    "pb": pb,
                    "ps": ps,
                    "ev_to_ebitda": ev_to_ebitda,
                    "roe": roe,
                    "roa": roa,
                    "profit_margin": profit_margin,
                    "operating_margin": operating_margin,
                    "gross_margin": gross_margin,
                    "debt_to_equity": debt_to_equity,
                    "revenue_growth": revenue_growth,
                    "earnings_growth": earnings_growth,
                    "dividend_yield": dividend_yield,
                    "current_ratio": current_ratio,
                    "quick_ratio": quick_ratio,
                    "free_cash_flow": free_cash_flow,
                    "operating_cash_flow": operating_cash_flow,
                    "market_cap": market_cap,
                    "total_revenue": total_revenue,
                    "ebitda": ebitda,
                    "beta": beta,
                    "eps": eps,
                    "is_financial": is_financial
                }
            }

        except Exception as e:
            return {
                "available": False,
                "reason": f"Fundamental calculation error: {str(e)}"
            }
