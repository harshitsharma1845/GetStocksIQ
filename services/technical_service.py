import pandas as pd
import numpy as np

class TechnicalService:
    """Calculates deterministic technical indicators, momentum metrics, and historical volatility from OHLCV data.
    Decoupled to keep Technicals, Momentum, and Risk pillars conceptually independent.
    """

    @staticmethod
    def calculate_indicators(history_df):
        """
        history_df: pandas DataFrame with Open, High, Low, Close, Volume columns
        """
        if history_df is None or history_df.empty:
            return {
                "available": False,
                "reason": "Historical price data is unavailable"
            }

        try:
            df = history_df.copy()
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0] for col in df.columns]

            for col in ["Close", "High", "Low", "Open", "Volume"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            df = df.dropna(subset=["Close"]).sort_index()

            if len(df) < 5:
                return {
                    "available": False,
                    "reason": "Insufficient historical data points (minimum 5 required)"
                }

            close = df["Close"]
            high = df["High"] if "High" in df.columns else close
            low = df["Low"] if "Low" in df.columns else close
            volume = df["Volume"] if "Volume" in df.columns else pd.Series(0, index=df.index)

            latest_price = float(close.iloc[-1])
            prev_price = float(close.iloc[-2]) if len(close) >= 2 else latest_price
            price_change_pct = ((latest_price - prev_price) / prev_price) * 100 if prev_price else 0.0

            # 1. Moving Averages
            sma_20 = float(close.tail(20).mean()) if len(close) >= 20 else float(close.mean())
            sma_50 = float(close.tail(50).mean()) if len(close) >= 50 else float(close.mean())
            sma_100 = float(close.tail(100).mean()) if len(close) >= 100 else float(close.mean())
            sma_200 = float(close.tail(200).mean()) if len(close) >= 200 else float(close.mean())

            ema_12 = float(close.ewm(span=12, adjust=False).mean().iloc[-1]) if len(close) >= 12 else latest_price
            ema_26 = float(close.ewm(span=26, adjust=False).mean().iloc[-1]) if len(close) >= 26 else latest_price

            # 2. RSI (14 periods)
            delta = close.diff()
            gain = delta.where(delta > 0, 0.0)
            loss = (-delta.where(delta < 0, 0.0))
            avg_gain = gain.rolling(window=14, min_periods=5).mean()
            avg_loss = loss.rolling(window=14, min_periods=5).mean()

            rs = avg_gain / (avg_loss + 1e-10)
            rsi_series = 100 - (100 / (1 + rs))
            rsi_14 = float(rsi_series.dropna().iloc[-1]) if not rsi_series.dropna().empty else 50.0
            rsi_14 = max(0.0, min(100.0, rsi_14))

            # 3. MACD (12, 26, 9)
            macd_series = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
            signal_series = macd_series.ewm(span=9, adjust=False).mean()
            macd_line = float(macd_series.iloc[-1]) if not macd_series.empty else 0.0
            macd_signal = float(signal_series.iloc[-1]) if not signal_series.empty else 0.0
            macd_hist = macd_line - macd_signal

            # 4. Bollinger Bands (20, 2)
            rolling_mean = close.rolling(window=20, min_periods=5).mean()
            rolling_std = close.rolling(window=20, min_periods=5).std()
            bb_middle = float(rolling_mean.iloc[-1]) if not rolling_mean.empty else latest_price
            bb_std = float(rolling_std.iloc[-1]) if not rolling_std.empty and not pd.isna(rolling_std.iloc[-1]) else 0.0
            bb_upper = bb_middle + (2 * bb_std)
            bb_lower = max(0.0, bb_middle - (2 * bb_std))
            bb_width = bb_upper - bb_lower
            bb_pct_b = (latest_price - bb_lower) / (bb_width + 1e-6) if bb_width > 0 else 0.5

            # 5. Average True Range (ATR 14)
            tr1 = high - low
            tr2 = (high - close.shift()).abs()
            tr3 = (low - close.shift()).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr_series = tr.rolling(window=14, min_periods=5).mean()
            atr_14 = float(atr_series.dropna().iloc[-1]) if not atr_series.dropna().empty else max(1.0, latest_price * 0.02)
            atr_pct = (atr_14 / latest_price) * 100 if latest_price > 0 else 2.5

            # 6. Support & Resistance Levels
            recent_lows = low.tail(60).nsmallest(5)
            recent_highs = high.tail(60).nlargest(5)
            support_1 = float(recent_lows.iloc[0]) if not recent_lows.empty else round(latest_price * 0.95, 2)
            support_2 = float(recent_lows.iloc[1]) if len(recent_lows) > 1 else round(latest_price * 0.90, 2)
            resistance_1 = float(recent_highs.iloc[0]) if not recent_highs.empty else round(latest_price * 1.05, 2)
            resistance_2 = float(recent_highs.iloc[1]) if len(recent_highs) > 1 else round(latest_price * 1.10, 2)

            # 7. 52-Week Range
            high_52 = float(high.tail(252).max()) if len(high) > 0 else latest_price
            low_52 = float(low.tail(252).min()) if len(low) > 0 else latest_price
            range_span = high_52 - low_52
            range_pos_52w = ((latest_price - low_52) / (range_span + 1e-6)) * 100 if range_span > 0 else 50.0

            # 8. Momentum Multi-Timeframe Returns
            n_bars = len(close)
            return_1m = float(((latest_price - close.iloc[-22]) / close.iloc[-22]) * 100) if n_bars >= 22 else None
            return_3m = float(((latest_price - close.iloc[-64]) / close.iloc[-64]) * 100) if n_bars >= 64 else None
            return_6m = float(((latest_price - close.iloc[-127]) / close.iloc[-127]) * 100) if n_bars >= 127 else None

            # Volume trends
            vol_clean = volume.dropna()
            recent_vol_5d = float(vol_clean.tail(5).mean()) if len(vol_clean) >= 5 else float(vol_clean.mean()) if not vol_clean.empty else 0.0
            avg_vol_30d = float(vol_clean.tail(30).mean()) if len(vol_clean) >= 30 else float(vol_clean.mean()) if not vol_clean.empty else 0.0
            relative_volume = (recent_vol_5d / avg_vol_30d) if avg_vol_30d > 0 else 1.0

            # 9. Historical Risk / Volatility & Max Drawdown
            daily_returns = close.pct_change().dropna()
            if len(daily_returns) >= 10:
                ann_volatility = float(daily_returns.std() * np.sqrt(252) * 100)
                cumulative = (1 + daily_returns).cumprod()
                peak = cumulative.cummax()
                drawdowns = (cumulative - peak) / peak
                max_drawdown = float(abs(drawdowns.min()) * 100)
            else:
                ann_volatility = None
                max_drawdown = None

            # ==============================================================
            # DETERMINISTIC TECHNICAL STRUCTURE SCORE (0–100)
            # Focus: Moving Average Alignments, RSI Oscillator, MACD, Bollinger position
            # (Note: Multi-timeframe percentage returns are scored in Momentum pillar)
            # ==============================================================
            t_scores = []
            t_weights = []

            # A. Moving Average Alignment (Weight: 0.40)
            ma_sub = []
            if len(close) >= 20:
                ma_sub.append(75.0 if latest_price >= sma_20 else 35.0)
            if len(close) >= 50:
                ma_sub.append(85.0 if latest_price >= sma_50 else 30.0)
            if len(close) >= 100:
                ma_sub.append(80.0 if latest_price >= sma_100 else 35.0)
            if len(close) >= 200:
                ma_sub.append(85.0 if latest_price >= sma_200 else 25.0)
            if len(close) >= 200:
                # Golden Cross / Death Cross
                ma_sub.append(90.0 if sma_50 >= sma_200 else 25.0)
            elif len(close) >= 26:
                # Shorter EMA trend proxy
                ma_sub.append(80.0 if ema_12 >= ema_26 else 35.0)

            if ma_sub:
                t_scores.append(sum(ma_sub) / len(ma_sub))
                t_weights.append(0.40)

            # B. RSI Oscillator Setup (Weight: 0.25)
            if 45 <= rsi_14 <= 65:
                rsi_score = 85.0 # Ideal bullish continuation zone
            elif 35 <= rsi_14 < 45:
                rsi_score = 60.0 # Neutral consolidation
            elif 65 < rsi_14 <= 75:
                rsi_score = 70.0 # Strong trend but approaching overbought
            elif rsi_14 > 75:
                rsi_score = 40.0 # Stretched / overbought risk
            elif 25 <= rsi_14 < 35:
                rsi_score = 45.0 # Bearish momentum
            else: # < 25
                rsi_score = 65.0 # Oversold mean-reversion opportunity
            t_scores.append(rsi_score)
            t_weights.append(0.25)

            # C. MACD Momentum Setup (Weight: 0.20)
            macd_score = 50.0
            if macd_line > macd_signal:
                macd_score = 80.0 if macd_hist > 0 else 65.0
            else:
                macd_score = 25.0 if macd_hist < 0 else 40.0
            t_scores.append(macd_score)
            t_weights.append(0.20)

            # D. Bollinger Bands Position (Weight: 0.15)
            if 0.30 <= bb_pct_b <= 0.80:
                bb_score = 80.0 # Healthy middle expansion
            elif 0.80 < bb_pct_b <= 1.05:
                bb_score = 65.0 # Riding upper band
            elif bb_pct_b > 1.05:
                bb_score = 40.0 # Stretched beyond 2 std dev
            elif 0.10 <= bb_pct_b < 0.30:
                bb_score = 50.0 # Lower range
            else:
                bb_score = 60.0 # Oversold lower band bounce
            t_scores.append(bb_score)
            t_weights.append(0.15)

            # Normalized technical score
            if t_scores and sum(t_weights) > 0:
                norm_w = [w / sum(t_weights) for w in t_weights]
                raw_t_score = sum(s * w for s, w in zip(t_scores, norm_w))
                technical_score = int(round(max(10, min(95, raw_t_score))))
            else:
                technical_score = 50

            if technical_score >= 70:
                trend_signal = "Bullish"
            elif technical_score <= 40:
                trend_signal = "Bearish"
            else:
                trend_signal = "Neutral"

            return {
                "available": True,
                "latest_price": round(latest_price, 2),
                "price_change_pct": round(price_change_pct, 2),
                "sma_20": round(sma_20, 2),
                "sma_50": round(sma_50, 2),
                "sma_100": round(sma_100, 2),
                "sma_200": round(sma_200, 2),
                "ema_12": round(ema_12, 2),
                "ema_26": round(ema_26, 2),
                "rsi_14": round(rsi_14, 1),
                "macd_line": round(macd_line, 2),
                "macd_signal": round(macd_signal, 2),
                "macd_histogram": round(macd_hist, 2),
                "bb_upper": round(bb_upper, 2),
                "bb_middle": round(bb_middle, 2),
                "bb_lower": round(bb_lower, 2),
                "bb_pct_b": round(bb_pct_b, 2),
                "atr_14": round(atr_14, 2),
                "atr_pct": round(atr_pct, 2),
                "support_1": round(support_1, 2),
                "support_2": round(support_2, 2),
                "resistance_1": round(resistance_1, 2),
                "resistance_2": round(resistance_2, 2),
                "high_52": round(high_52, 2),
                "low_52": round(low_52, 2),
                "technical_score": technical_score,
                "trend_signal": trend_signal,
                "data_points": n_bars,
                # Exported for Momentum & Risk Pillars
                "momentum_metrics": {
                    "return_1m": round(return_1m, 2) if return_1m is not None else None,
                    "return_3m": round(return_3m, 2) if return_3m is not None else None,
                    "return_6m": round(return_6m, 2) if return_6m is not None else None,
                    "range_position_52w": round(range_pos_52w, 2),
                    "relative_volume": round(relative_volume, 2),
                    "avg_vol_30d": round(avg_vol_30d, 0)
                },
                "risk_metrics": {
                    "annualized_volatility": round(ann_volatility, 2) if ann_volatility is not None else None,
                    "max_drawdown": round(max_drawdown, 2) if max_drawdown is not None else None,
                    "atr_pct": round(atr_pct, 2)
                }
            }

        except Exception as e:
            return {
                "available": False,
                "reason": f"Technical calculation error: {str(e)}"
            }
