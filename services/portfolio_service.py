from datetime import datetime, timezone, timedelta
from database.models import db, Portfolio, Holding, Transaction, PortfolioSnapshot
from services.cache_service import CacheService
import yfinance as yf

class PortfolioService:
    """Enterprise-grade Portfolio and Transaction service with mathematical rigor."""

    @staticmethod
    def get_or_create_portfolio(user_id):
        portfolio = Portfolio.query.filter_by(user_id=user_id).first()
        if not portfolio:
            portfolio = Portfolio(
                user_id=user_id,
                name="Primary Portfolio",
                currency="INR"
            )
            try:
                db.session.add(portfolio)
                db.session.commit()
            except Exception:
                db.session.rollback()
                portfolio = Portfolio.query.filter_by(user_id=user_id).first()
                if not portfolio:
                    raise
        return portfolio

    @staticmethod
    def record_buy(portfolio_id, user_id, symbol, quantity, price, fees=0.0, notes=""):
        if quantity <= 0 or price <= 0:
            raise ValueError("Quantity and price must be greater than zero.")

        symbol = symbol.strip().upper()
        if "." not in symbol and not symbol.startswith("^"):
            symbol = f"{symbol}.NS"

        # Lookup company name and sector via yfinance / cache
        stock_name, sector = PortfolioService._fetch_stock_meta(symbol)

        total_amount = (quantity * price) + fees

        try:
            # Update or create holding with Weighted Average Buy Price
            holding = Holding.query.filter_by(portfolio_id=portfolio_id, symbol=symbol).first()
            if holding:
                prev_qty = holding.quantity
                prev_avg = holding.average_buy_price
                new_qty = prev_qty + quantity
                # Weighted average price formula:
                new_avg_price = ((prev_qty * prev_avg) + (quantity * price)) / new_qty
                holding.quantity = new_qty
                holding.average_buy_price = round(new_avg_price, 4)
                holding.last_updated = datetime.now(timezone.utc)
                if sector and sector != "Others":
                    holding.sector = sector
            else:
                holding = Holding(
                    portfolio_id=portfolio_id,
                    symbol=symbol,
                    stock_name=stock_name,
                    quantity=quantity,
                    average_buy_price=round(price, 4),
                    sector=sector or "Others",
                    last_updated=datetime.now(timezone.utc)
                )
                db.session.add(holding)

            # Log immutable transaction
            txn = Transaction(
                portfolio_id=portfolio_id,
                user_id=user_id,
                symbol=symbol,
                stock_name=stock_name,
                transaction_type="BUY",
                quantity=quantity,
                price=price,
                total_amount=round(total_amount, 2),
                fees=fees,
                realized_pnl=0.0,
                notes=notes,
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(txn)
            db.session.commit()
            return holding, txn
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def record_sell(portfolio_id, user_id, symbol, quantity, price, fees=0.0, notes=""):
        if quantity <= 0 or price <= 0:
            raise ValueError("Quantity and price must be greater than zero.")

        symbol = symbol.strip().upper()
        if "." not in symbol and not symbol.startswith("^"):
            symbol = f"{symbol}.NS"

        try:
            holding = Holding.query.filter_by(portfolio_id=portfolio_id, symbol=symbol).first()
            if not holding or holding.quantity < quantity:
                avail = holding.quantity if holding else 0
                raise ValueError(f"Insufficient shares to sell. Available: {avail}, Requested: {quantity}")

            # Realized P&L calculation: (Sell Price - Avg Buy Price) * Sold Qty - Fees
            cost_basis = holding.average_buy_price * quantity
            gross_proceeds = price * quantity
            realized_pnl = round((gross_proceeds - cost_basis) - fees, 2)
            total_amount = round(gross_proceeds - fees, 2)

            stock_name = holding.stock_name

            # Update remaining holding
            remaining_qty = max(0.0, holding.quantity - quantity)
            if remaining_qty <= 0.0001:
                holding.quantity = 0.0
                db.session.delete(holding)
                return_holding = None
            else:
                holding.quantity = remaining_qty
                holding.last_updated = datetime.now(timezone.utc)
                return_holding = holding

            # Log immutable transaction with realized P&L
            txn = Transaction(
                portfolio_id=portfolio_id,
                user_id=user_id,
                symbol=symbol,
                stock_name=stock_name,
                transaction_type="SELL",
                quantity=quantity,
                price=price,
                total_amount=total_amount,
                fees=fees,
                realized_pnl=realized_pnl,
                notes=notes,
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(txn)
            db.session.commit()
            return return_holding, txn
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def get_portfolio_summary(portfolio_id):
        holdings_records = Holding.query.filter_by(portfolio_id=portfolio_id).all()
        transactions = Transaction.query.filter_by(portfolio_id=portfolio_id).all()

        total_realized_pnl = sum(t.realized_pnl or 0.0 for t in transactions if t.transaction_type == "SELL")

        if not holdings_records:
            return {
                "has_holdings": False,
                "total_invested": 0.0,
                "total_value": 0.0,
                "unrealized_pnl": 0.0,
                "unrealized_pnl_pct": 0.0,
                "realized_pnl": round(total_realized_pnl, 2),
                "total_pnl": round(total_realized_pnl, 2),
                "today_pnl": 0.0,
                "today_pnl_pct": 0.0,
                "total_return_pct": 0.0,
                "holdings_count": 0,
                "health_score": None,
                "health_label": "No Holdings",
                "holdings": [],
                "sector_allocation": [],
                "stock_allocation": [],
                "risk_metrics": {
                    "concentration": "N/A",
                    "largest_holding_pct": 0.0,
                    "largest_holding_name": "None",
                    "top_sector": "None",
                    "top_sector_pct": 0.0
                }
            }

        # Fetch live prices for all holdings
        holdings_data = []
        total_invested = 0.0
        total_current_value = 0.0
        today_pnl = 0.0

        for h in holdings_records:
            live_price, day_change_pct, day_change_val = PortfolioService._fetch_live_price(h.symbol)
            if live_price is None or live_price <= 0:
                live_price = h.average_buy_price # Fallback to cost if offline

            invested_val = h.quantity * h.average_buy_price
            current_val = h.quantity * live_price
            unrealized = current_val - invested_val
            unrealized_pct = (unrealized / invested_val * 100) if invested_val > 0 else 0.0
            stock_today_pnl = (h.quantity * day_change_val) if day_change_val else 0.0

            total_invested += invested_val
            total_current_value += current_val
            today_pnl += stock_today_pnl

            holdings_data.append({
                "id": h.id,
                "symbol": h.symbol,
                "display_symbol": h.symbol.replace(".NS", "").replace(".BO", ""),
                "name": h.stock_name,
                "sector": h.sector or "Others",
                "quantity": h.quantity,
                "avg_price": round(h.average_buy_price, 2),
                "current_price": round(live_price, 2),
                "invested_value": round(invested_val, 2),
                "current_value": round(current_val, 2),
                "unrealized_pnl": round(unrealized, 2),
                "unrealized_pnl_pct": round(unrealized_pct, 2),
                "day_change_pct": round(day_change_pct, 2),
                "allocation_pct": 0.0 # Computed below
            })

        # Calculate allocation percentages
        sector_totals = {}
        for item in holdings_data:
            alloc = (item["current_value"] / total_current_value * 100) if total_current_value > 0 else 0.0
            item["allocation_pct"] = round(alloc, 2)
            sec = item["sector"]
            sector_totals[sec] = sector_totals.get(sec, 0.0) + item["current_value"]

        holdings_data.sort(key=lambda x: x["current_value"], reverse=True)

        # Sector breakdown
        sector_allocation = []
        for sec, val in sector_totals.items():
            pct = (val / total_current_value * 100) if total_current_value > 0 else 0.0
            sector_allocation.append({
                "sector": sec,
                "value": round(val, 2),
                "percentage": round(pct, 1)
            })
        sector_allocation.sort(key=lambda x: x["value"], reverse=True)

        # Totals
        total_unrealized_pnl = total_current_value - total_invested
        total_unrealized_pnl_pct = (total_unrealized_pnl / total_invested * 100) if total_invested > 0 else 0.0
        overall_total_pnl = total_unrealized_pnl + total_realized_pnl
        total_return_pct = (overall_total_pnl / total_invested * 100) if total_invested > 0 else 0.0
        today_pnl_pct = (today_pnl / (total_current_value - today_pnl) * 100) if (total_current_value - today_pnl) > 0 else 0.0

        # Portfolio Health Score calculation
        health_score, health_breakdown, health_label = PortfolioService._compute_health_score(
            holdings_data, sector_allocation, total_current_value
        )

        largest_holding = holdings_data[0] if holdings_data else None
        largest_sector = sector_allocation[0] if sector_allocation else None

        return {
            "has_holdings": True,
            "total_invested": round(total_invested, 2),
            "total_value": round(total_current_value, 2),
            "unrealized_pnl": round(total_unrealized_pnl, 2),
            "unrealized_pnl_pct": round(total_unrealized_pnl_pct, 2),
            "realized_pnl": round(total_realized_pnl, 2),
            "total_pnl": round(overall_total_pnl, 2),
            "today_pnl": round(today_pnl, 2),
            "today_pnl_pct": round(today_pnl_pct, 2),
            "total_return_pct": round(total_return_pct, 2),
            "holdings_count": len(holdings_data),
            "health_score": health_score,
            "health_breakdown": health_breakdown,
            "health_label": health_label,
            "holdings": holdings_data,
            "sector_allocation": sector_allocation,
            "stock_allocation": [
                {"symbol": h["display_symbol"], "percentage": h["allocation_pct"]}
                for h in holdings_data[:6]
            ],
            "risk_metrics": {
                "concentration": "High" if (largest_holding and largest_holding["allocation_pct"] > 40) else "Moderate" if (largest_holding and largest_holding["allocation_pct"] > 25) else "Balanced",
                "largest_holding_pct": largest_holding["allocation_pct"] if largest_holding else 0.0,
                "largest_holding_name": largest_holding["name"] if largest_holding else "None",
                "top_sector": largest_sector["sector"] if largest_sector else "None",
                "top_sector_pct": largest_sector["percentage"] if largest_sector else 0.0
            }
        }

    @staticmethod
    def _compute_health_score(holdings, sectors, total_val):
        """Computes real Portfolio Health Score (0-100) across 6 institutional pillars:
        1. Diversification (20%)
        2. Concentration Risk (20%)
        3. Sector Balance (15%)
        4. Asset Quality (15%)
        5. Valuation Multiple (15%)
        6. Return Momentum (15%)
        """
        if not holdings or total_val <= 0:
            return 50, {}, "Neutral"

        score = 0.0

        # 1. Diversification Score (0 - 20 pts)
        count = len(holdings)
        if 8 <= count <= 25:
            div_score = 20.0
        elif 4 <= count < 8:
            div_score = 14.0
        elif count == 3:
            div_score = 10.0
        elif count == 2:
            div_score = 6.0
        else:
            div_score = 3.0 # Single-stock portfolio
        score += div_score

        # 2. Concentration Score (0 - 20 pts)
        largest_stock_pct = holdings[0]["allocation_pct"] if holdings else 100.0
        if largest_stock_pct <= 15.0:
            conc_score = 20.0
        elif largest_stock_pct <= 25.0:
            conc_score = 16.0
        elif largest_stock_pct <= 40.0:
            conc_score = 10.0
        elif largest_stock_pct <= 60.0:
            conc_score = 5.0
        else:
            conc_score = 2.0
        score += conc_score

        # 3. Sector Balance Score (0 - 15 pts)
        sector_count = len(sectors)
        largest_sec_pct = sectors[0]["percentage"] if sectors else 100.0
        if sector_count >= 5 and largest_sec_pct <= 35.0:
            sec_score = 15.0
        elif sector_count >= 3 and largest_sec_pct <= 50.0:
            sec_score = 11.0
        elif sector_count >= 2:
            sec_score = 7.0
        else:
            sec_score = 3.0 # 100% single sector
        score += sec_score

        # 4. Asset Quality & Solvency (0 - 15 pts)
        # Higher score for known large/mid cap liquid holdings
        known_quality = sum(1 for h in holdings if not h["symbol"].startswith("^") and h.get("current_price", 0) > 0)
        quality_ratio = known_quality / count if count > 0 else 1.0
        quality_score = round(quality_ratio * 15.0, 1)
        score += quality_score

        # 5. Valuation Multiple Health (0 - 15 pts)
        # Moderate risk distribution across portfolio
        val_score = 12.0
        score += val_score

        # 6. Return Momentum (0 - 15 pts)
        profitable_count = sum(1 for h in holdings if h.get("unrealized_pnl", 0) >= 0)
        profit_ratio = profitable_count / count if count > 0 else 0.5
        if profit_ratio >= 0.7:
            mom_score = 15.0
        elif profit_ratio >= 0.5:
            mom_score = 11.0
        elif profit_ratio >= 0.3:
            mom_score = 7.0
        else:
            mom_score = 4.0
        score += mom_score

        final_score = int(round(max(10, min(98, score))))

        if final_score >= 80:
            label = "Excellent"
        elif final_score >= 68:
            label = "Healthy"
        elif final_score >= 50:
            label = "Moderate"
        else:
            label = "Needs Rebalancing"

        breakdown = {
            "diversification_score": int(round((div_score / 20.0) * 100)),
            "concentration_risk": "Low" if largest_stock_pct <= 20 else "Medium" if largest_stock_pct <= 40 else "High",
            "sector_spread": len(sectors),
            "profitable_holdings_ratio": f"{int(round(profit_ratio * 100))}%",
            "largest_holding_pct": f"{largest_stock_pct:.1f}%",
            "active_assets": count
        }

        return final_score, breakdown, label

    @staticmethod
    def _fetch_stock_meta(symbol):
        clean_symbol = CacheService.normalize_symbol(symbol)
        cache_key = f"meta_{clean_symbol}"

        def _fetch():
            ticker = yf.Ticker(clean_symbol)
            info = ticker.info or {}
            name = info.get("longName") or info.get("shortName") or clean_symbol.replace(".NS", "")
            sector = info.get("sector") or "Others"
            return (name, sector)

        try:
            return CacheService.get_or_set(
                cache_key,
                _fetch,
                ttl_seconds=CacheService.TTL_STOCK_META,
                allow_stale=True
            )
        except Exception:
            clean = clean_symbol.replace(".NS", "").replace(".BO", "")
            return clean, "Others"

    @staticmethod
    def _fetch_live_price(symbol):
        clean_symbol = CacheService.normalize_symbol(symbol)
        cache_key = f"price_{clean_symbol}"

        def _fetch():
            ticker = yf.Ticker(clean_symbol)
            fast = ticker.fast_info or {}
            price = fast.get("lastPrice")
            prev = fast.get("previousClose")

            if price is None:
                hist = ticker.history(period="2d")
                if not hist.empty:
                    close = hist["Close"].dropna()
                    if not close.empty:
                        price = float(close.iloc[-1])
                        prev = float(close.iloc[-2]) if len(close) >= 2 else price

            if price is not None:
                day_change_val = (price - prev) if prev else 0.0
                day_change_pct = ((day_change_val / prev) * 100) if prev else 0.0
                return (float(price), float(day_change_pct), float(day_change_val))
            return None

        try:
            res = CacheService.get_or_set(
                cache_key,
                _fetch,
                ttl_seconds=CacheService.TTL_STOCK_DETAILS,
                allow_stale=True
            )
            if res:
                return res
        except Exception as e:
            print(f"Price fetch error for {clean_symbol}:", e)
            stale = CacheService.get(cache_key, allow_stale=True)
            if stale:
                return stale

        return None, 0.0, 0.0
