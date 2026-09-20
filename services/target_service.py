class TargetService:
    """Calculates risk-adjusted Target Price, Stop Loss, and Risk/Reward ratio using ATR and Support/Resistance levels."""

    @staticmethod
    def calculate_targets(current_price, technicals_data):
        if not current_price or current_price <= 0:
            return {
                "available": False,
                "target_price": "Not available",
                "stop_loss": "Not available",
                "risk_reward_ratio": "N/A"
            }

        if not technicals_data or not technicals_data.get("available"):
            # If technicals unavailable, return clean unavailable state
            return {
                "available": False,
                "target_price": "Not available",
                "stop_loss": "Not available",
                "risk_reward_ratio": "N/A"
            }

        try:
            atr = technicals_data.get("atr_14") or technicals_data.get("risk_metrics", {}).get("atr") or (current_price * 0.02)
            support_1 = technicals_data.get("support_1") or (current_price - (1.5 * atr))
            resistance_1 = technicals_data.get("resistance_1") or (current_price + (2.5 * atr))
            trend_signal = technicals_data.get("trend_signal") or technicals_data.get("trend") or "Neutral"

            # Determine stop loss below primary support level or 1.5 * ATR
            if support_1 < current_price:
                stop_loss = max(current_price * 0.70, min(current_price - (0.5 * atr), support_1 - (0.5 * atr)))
            else:
                stop_loss = current_price - (1.8 * atr)

            risk_per_share = current_price - stop_loss
            if risk_per_share <= 0:
                risk_per_share = max(1.0, current_price * 0.03)
                stop_loss = current_price - risk_per_share

            # Target 1 based on resistance or minimum 2:1 risk/reward
            if trend_signal == "Bullish":
                min_reward = risk_per_share * 2.2
                target_1 = max(current_price + min_reward, resistance_1)
            elif trend_signal == "Bearish":
                min_reward = risk_per_share * 1.5
                target_1 = current_price + min_reward
            else: # Neutral
                min_reward = risk_per_share * 1.8
                target_1 = max(current_price + min_reward, resistance_1)

            reward_per_share = target_1 - current_price
            rr_ratio = round(reward_per_share / (risk_per_share + 1e-6), 1)

            return {
                "available": True,
                "current_price": round(current_price, 2),
                "target_price": round(target_1, 2),
                "stop_loss": round(stop_loss, 2),
                "risk_per_share": round(risk_per_share, 2),
                "reward_per_share": round(reward_per_share, 2),
                "risk_reward_ratio": f"1:{rr_ratio}",
                "time_horizon": "3-6 Months" if trend_signal == "Bullish" else "Monitored",
            }

        except Exception:
            return {
                "available": False,
                "target_price": "Not available",
                "stop_loss": "Not available",
                "risk_reward_ratio": "N/A"
            }
