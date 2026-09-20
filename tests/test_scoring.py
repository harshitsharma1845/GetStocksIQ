import unittest
import os
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.scoring_service import ScoringEngine
from services.fundamental_service import FundamentalService
from services.technical_service import TechnicalService
from services.target_service import TargetService


class TestScoringAndTechnicals(unittest.TestCase):

    def test_scoring_engine_composite_normal(self):
        fundamentals = {
            "available": True,
            "fundamental_score": 85,
            "raw_metrics": {
                "pe": 18.5,
                "forward_pe": 16.0,
                "peg_ratio": 1.1,
                "pb": 2.2,
                "ps": 2.5,
                "ev_to_ebitda": 12.0,
                "roe": 0.22,
                "debt_to_equity": 25.0,
                "revenue_growth": 0.18,
                "dividend_yield": 0.025,
                "market_cap": 1500000000000,
                "free_cash_flow": 50000000000,
                "beta": 0.95
            },
        }

        technicals = {
            "available": True,
            "technical_score": 80,
            "latest_price": 2500.0,
            "sma_20": 2420.0,
            "sma_50": 2350.0,
            "sma_200": 2100.0,
            "rsi_14": 62.5,
            "high_52": 2600.0,
            "low_52": 2000.0,
            "atr_14": 45.0,
            "trend_signal": "Bullish",
            "momentum_metrics": {
                "return_1m": 4.5,
                "return_3m": 12.0,
                "return_6m": 22.0,
                "range_position_52w": 83.3,
                "relative_volume": 1.25,
                "avg_vol_30d": 1500000
            },
            "risk_metrics": {
                "annualized_volatility": 19.5,
                "max_drawdown": 8.5,
                "atr_pct": 1.8
            }
        }

        eval_result = ScoringEngine.evaluate_stock(
            fundamentals_data=fundamentals,
            technicals_data=technicals,
            news_sentiment_score=75,
        )

        self.assertTrue(0 <= eval_result["overall_score"] <= 100)
        self.assertIn(eval_result["signal"], ["Strong Buy", "Buy"])
        self.assertGreaterEqual(eval_result["confidence"], 50)
        self.assertGreater(len(eval_result["strengths"]), 0)
        self.assertIn("factor_scores", eval_result)
        self.assertEqual(eval_result["factor_scores"]["fundamentals"], 85)
        self.assertEqual(eval_result["factor_scores"]["technicals"], 80)
        self.assertIn("valuation", eval_result["factor_scores"])
        self.assertIn("momentum", eval_result["factor_scores"])
        self.assertIn("risk", eval_result["factor_scores"])
        self.assertIn("liquidity", eval_result["factor_scores"])
        self.assertEqual(eval_result["risk_label"], "Low Risk")

    def test_scoring_engine_missing_metrics_graceful_handling(self):
        # Sparse fundamentals and technicals
        fundamentals = {
            "available": True,
            "fundamental_score": 60,
            "raw_metrics": {
                "pe": 22.0,
                # Missing PEG, PB, PS, EV/EBITDA, Beta, Debt
            }
        }
        technicals = {
            "available": True,
            "technical_score": 55,
            "latest_price": 500.0,
            "momentum_metrics": {
                "return_1m": 1.5,
                # Missing 3m, 6m
            }
        }

        eval_result = ScoringEngine.evaluate_stock(
            fundamentals_data=fundamentals,
            technicals_data=technicals,
            news_sentiment_score=50
        )

        self.assertTrue(0 <= eval_result["overall_score"] <= 100)
        self.assertIn(eval_result["signal"], ["Hold", "Buy", "Reduce"])
        self.assertIn("missing_metrics", eval_result)
        self.assertTrue(len(eval_result["missing_metrics"]) > 0)
        self.assertTrue(0 <= eval_result["data_quality"] <= 100)

    def test_scoring_engine_negative_earnings_and_unprofitable_company(self):
        fundamentals = {
            "available": True,
            "fundamental_score": 25,
            "raw_metrics": {
                "pe": -15.0, # Negative earnings
                "pb": 1.2,
                "roe": -0.15,
                "debt_to_equity": 240.0,
                "revenue_growth": -0.10,
                "free_cash_flow": -10000000,
            }
        }
        technicals = {
            "available": True,
            "technical_score": 30,
            "latest_price": 45.0,
            "rsi_14": 28.0,
            "trend_signal": "Bearish",
            "momentum_metrics": {
                "return_1m": -18.0,
                "return_3m": -35.0,
                "return_6m": -45.0,
                "range_position_52w": 12.0,
            },
            "risk_metrics": {
                "annualized_volatility": 58.0,
                "max_drawdown": 52.0,
                "atr_pct": 5.2
            }
        }

        eval_result = ScoringEngine.evaluate_stock(
            fundamentals_data=fundamentals,
            technicals_data=technicals,
            news_sentiment_score=30
        )

        self.assertTrue(0 <= eval_result["overall_score"] <= 100)
        self.assertIn(eval_result["signal"], ["Avoid", "Reduce"])
        self.assertEqual(eval_result["risk_label"], "High Risk")
        self.assertTrue(any("Debt" in r or "Drawdown" in r or "Volatility" in r or "Equity" in r for r in eval_result["risks"]))

    def test_scoring_engine_extreme_valuation(self):
        fundamentals = {
            "available": True,
            "fundamental_score": 75,
            "raw_metrics": {
                "pe": 180.0, # Astronomical P/E
                "forward_pe": 120.0,
                "peg_ratio": 4.5,
                "pb": 25.0,
                "ps": 30.0,
                "roe": 0.25,
            }
        }
        technicals = {
            "available": True,
            "technical_score": 70,
            "latest_price": 4000.0,
            "momentum_metrics": {
                "return_1m": 12.0,
                "return_3m": 35.0,
            }
        }

        eval_result = ScoringEngine.evaluate_stock(
            fundamentals_data=fundamentals,
            technicals_data=technicals,
            news_sentiment_score=60
        )

        # Valuation score should be penalized for extreme multiples
        val_score = eval_result["factor_scores"]["valuation"]
        self.assertLessEqual(val_score, 45)
        self.assertTrue(0 <= eval_result["overall_score"] <= 100)

    def test_fundamental_service_extraction_and_scoring(self):
        mock_info = {
            "returnOnEquity": 0.24,
            "returnOnAssets": 0.12,
            "profitMargins": 0.16,
            "operatingMargins": 0.21,
            "revenueGrowth": 0.15,
            "earningsGrowth": 0.18,
            "debtToEquity": 15.0,
            "currentRatio": 2.1,
            "freeCashflow": 25000000000,
            "totalRevenue": 100000000000,
            "trailingPE": 22.5,
            "priceToBook": 3.1,
            "marketCap": 2000000000000,
            "sector": "Technology",
            "industry": "Software"
        }

        res = FundamentalService.extract_fundamentals(mock_info)
        self.assertTrue(res["available"])
        self.assertGreaterEqual(res["fundamental_score"], 75)
        self.assertEqual(res["raw_metrics"]["roe"], 0.24)
        self.assertFalse(res["raw_metrics"]["is_financial"])

    def test_technical_service_synthetic_data(self):
        dates = pd.date_range(end="2026-08-18", periods=80, freq="B")
        prices = [100.0 + (i * 1.5) + (i % 3) for i in range(80)]

        df = pd.DataFrame(
            {
                "Open": [p - 1.0 for p in prices],
                "High": [p + 2.0 for p in prices],
                "Low": [p - 2.0 for p in prices],
                "Close": prices,
                "Volume": [1000000 + (i * 5000) for i in range(80)],
            },
            index=dates,
        )

        indicators = TechnicalService.calculate_indicators(df)

        self.assertTrue(indicators["available"])
        self.assertEqual(indicators["latest_price"], prices[-1])
        self.assertGreater(indicators["sma_20"], 0)
        self.assertGreater(indicators["sma_50"], 0)
        self.assertTrue(0 <= indicators["rsi_14"] <= 100)
        self.assertGreaterEqual(indicators["bb_upper"], indicators["bb_middle"])
        self.assertGreaterEqual(indicators["bb_middle"], indicators["bb_lower"])
        self.assertGreater(indicators["atr_14"], 0)
        self.assertGreaterEqual(indicators["technical_score"], 10)
        self.assertIn("momentum_metrics", indicators)
        self.assertIn("risk_metrics", indicators)
        self.assertIsNotNone(indicators["momentum_metrics"]["return_1m"])
        self.assertIsNotNone(indicators["risk_metrics"]["annualized_volatility"])

    def test_target_service_atr(self):
        technicals = {
            "available": True,
            "latest_price": 1000.0,
            "atr_14": 25.0,
            "support_1": 960.0,
            "resistance_1": 1060.0,
            "trend_signal": "Bullish",
        }

        targets = TargetService.calculate_targets(1000.0, technicals)

        self.assertTrue(targets["available"])
        self.assertGreater(targets["target_price"], 1000.0)
        self.assertLess(targets["stop_loss"], 1000.0)
        self.assertIn("1:", targets["risk_reward_ratio"])


if __name__ == "__main__":
    unittest.main()

