import unittest
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from database.models import User, Portfolio, Holding, Transaction, Watchlist
from flask_bcrypt import Bcrypt
from services.portfolio_service import PortfolioService
from services.technical_service import TechnicalService
from services.fundamental_service import FundamentalService
from services.news_service import NewsService
from services.scoring_service import ScoringEngine
from services.target_service import TargetService
from services.llm_service import LLMService


class ComprehensiveQATestSuite(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.bcrypt = Bcrypt(app)
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

        # Clean existing test users if any
        for email in ["alpha@test.com", "beta@test.com", "gamma@test.com", "qa@test.com"]:
            u = User.query.filter_by(email=email).first()
            if u:
                for p in Portfolio.query.filter_by(user_id=u.id).all():
                    Holding.query.filter_by(portfolio_id=p.id).delete()
                    Transaction.query.filter_by(portfolio_id=p.id).delete()
                    db.session.delete(p)
                Watchlist.query.filter_by(user_id=u.id).delete()
                db.session.delete(u)
        db.session.commit()

        # Create User A
        self.user_a = User(
            full_name="User Alpha",
            email="alpha@test.com",
            password=self.bcrypt.generate_password_hash("AlphaPass123").decode("utf-8"),
        )
        # Create User B
        self.user_b = User(
            full_name="User Beta",
            email="beta@test.com",
            password=self.bcrypt.generate_password_hash("BetaPass123").decode("utf-8"),
        )
        db.session.add_all([self.user_a, self.user_b])
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        try:
            for email in ["alpha@test.com", "beta@test.com", "gamma@test.com", "qa@test.com"]:
                u = User.query.filter_by(email=email).first()
                if u:
                    for p in Portfolio.query.filter_by(user_id=u.id).all():
                        Holding.query.filter_by(portfolio_id=p.id).delete()
                        Transaction.query.filter_by(portfolio_id=p.id).delete()
                        db.session.delete(p)
                    Watchlist.query.filter_by(user_id=u.id).delete()
                    db.session.delete(u)
            db.session.commit()
        except Exception:
            db.session.rollback()
        finally:
            db.session.remove()
            self.app_context.pop()

    def login(self, email, password):
        return self.client.post(
            "/login",
            data={"email": email, "password": password},
            follow_redirects=True,
        )

    # -------------------------------------------------------------
    # 1. SECURITY & CROSS-USER ISOLATION TESTS
    # -------------------------------------------------------------
    def test_cross_user_portfolio_isolation(self):
        """Verify User A cannot view, mutate, or sell User B's holdings."""
        # Ensure clean state for both test users
        port_a = PortfolioService.get_or_create_portfolio(self.user_a.id)
        port_b = PortfolioService.get_or_create_portfolio(self.user_b.id)
        Holding.query.filter_by(portfolio_id=port_a.id).delete()
        Holding.query.filter_by(portfolio_id=port_b.id).delete()
        Transaction.query.filter_by(portfolio_id=port_a.id).delete()
        Transaction.query.filter_by(portfolio_id=port_b.id).delete()
        db.session.commit()

        # User B buys 10 shares of INFY.NS
        h_b, _ = PortfolioService.record_buy(
            port_b.id, self.user_b.id, "INFY.NS", 10, 1500.0
        )

        # Login as User A
        self.login("alpha@test.com", "AlphaPass123")

        # User A checks their portfolio summary
        res = self.client.get("/api/portfolio/summary")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)["data"]
        # User A's portfolio must be completely empty
        self.assertFalse(data["has_holdings"])
        self.assertEqual(data["holdings_count"], 0)

        # User A attempts to SELL User B's INFY.NS (User A has 0 shares)
        res = self.client.post(
            "/api/portfolio/sell",
            json={"symbol": "INFY.NS", "quantity": 5, "price": 1600.0},
        )
        self.assertEqual(res.status_code, 400)
        err_data = json.loads(res.data)
        self.assertFalse(err_data["success"])
        self.assertIn("Insufficient shares", err_data["message"])

        # User B's holding must remain completely intact
        h_b_refreshed = Holding.query.filter_by(id=h_b.id).first()
        self.assertEqual(h_b_refreshed.quantity, 10)

    def test_unauthenticated_api_protection(self):
        """Verify all private endpoints reject unauthenticated access."""
        protected_get = [
            "/api/portfolio/summary",
            "/api/portfolio/transactions",
            "/dashboard",
            "/portfolio",
            "/watchlist",
        ]
        for url in protected_get:
            res = self.client.get(url)
            self.assertIn(
                res.status_code,
                [302, 401],
                f"Endpoint {url} not protected!",
            )

        protected_post = [
            "/api/portfolio/buy",
            "/api/portfolio/sell",
            "/api/portfolio/analyze-ai",
            "/api/ask-ai",
            "/watchlist/add",
        ]
        for url in protected_post:
            res = self.client.post(url, json={})
            self.assertIn(
                res.status_code,
                [302, 401],
                f"Endpoint {url} not protected!",
            )

    # -------------------------------------------------------------
    # 2. FULL 23-FLOW END-TO-END VERIFICATION
    # -------------------------------------------------------------
    def test_end_to_end_user_lifecycle_and_trading_flows(self):
        """Test complete user journey: Signup -> Login -> Trade -> Analysis -> AI -> Watchlist -> Logout."""
        # 1. Signup new user
        signup_res = self.client.post(
            "/register",
            data={
                "fullname": "QA Tester",
                "email": "qa@test.com",
                "password": "QAPassword123!",
                "confirm": "QAPassword123!",
            },
            follow_redirects=True,
        )
        self.assertEqual(signup_res.status_code, 200)

        # 2. Login
        login_res = self.login("qa@test.com", "QAPassword123!")
        self.assertEqual(login_res.status_code, 200)

        # 3. Dashboard empty state check
        dash_res = self.client.get("/dashboard")
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b"Portfolio Value", dash_res.data)

        # 4. Stock Search API
        search_res = self.client.get("/api/search-stocks?q=TCS")
        self.assertEqual(search_res.status_code, 200)
        stocks = json.loads(search_res.data)
        self.assertGreater(len(stocks), 0)

        # 5. First BUY: 10 TCS.NS @ ₹3,500 with ₹20 fee
        buy1_res = self.client.post(
            "/api/portfolio/buy",
            json={
                "symbol": "TCS.NS",
                "quantity": 10,
                "price": 3500.0,
                "fees": 20.0,
                "notes": "First accumulation",
            },
        )
        self.assertEqual(buy1_res.status_code, 200)
        buy1_data = json.loads(buy1_res.data)
        self.assertTrue(buy1_data["success"])
        self.assertEqual(buy1_data["holding"]["quantity"], 10)
        self.assertEqual(buy1_data["holding"]["avg_price"], 3500.0)

        # 6. Second BUY: 10 TCS.NS @ ₹3,700 with ₹20 fee
        # Weighted Average: (10*3500 + 10*3700) / 20 = 3600.0
        buy2_res = self.client.post(
            "/api/portfolio/buy",
            json={
                "symbol": "TCS.NS",
                "quantity": 10,
                "price": 3700.0,
                "fees": 20.0,
                "notes": "Second accumulation",
            },
        )
        self.assertEqual(buy2_res.status_code, 200)
        buy2_data = json.loads(buy2_res.data)
        self.assertTrue(buy2_data["success"])
        self.assertEqual(buy2_data["holding"]["quantity"], 20)
        self.assertEqual(buy2_data["holding"]["avg_price"], 3600.0)

        # 7. Add another stock: 5 RELIANCE.NS @ ₹2,800
        buy3_res = self.client.post(
            "/api/portfolio/buy",
            json={
                "symbol": "RELIANCE.NS",
                "quantity": 5,
                "price": 2800.0,
                "fees": 10.0,
                "notes": "Energy sector allocation",
            },
        )
        self.assertEqual(buy3_res.status_code, 200)

        # 8. Check Portfolio Summary
        sum_res = self.client.get("/api/portfolio/summary")
        self.assertEqual(sum_res.status_code, 200)
        summary = json.loads(sum_res.data)["data"]
        self.assertTrue(summary["has_holdings"])
        self.assertEqual(summary["holdings_count"], 2)
        # Total invested = (20 * 3600) + (5 * 2800) = 72000 + 14000 = 86000.0
        self.assertEqual(summary["total_invested"], 86000.0)
        self.assertGreater(summary["health_score"], 0)

        # 9. Partial SELL: 5 TCS.NS @ ₹4,000 with ₹15 fee
        # Realized P&L = (4000 - 3600) * 5 - 15 = 2000 - 15 = 1985.0
        sell1_res = self.client.post(
            "/api/portfolio/sell",
            json={
                "symbol": "TCS.NS",
                "quantity": 5,
                "price": 4000.0,
                "fees": 15.0,
                "notes": "Partial profit booking",
            },
        )
        self.assertEqual(sell1_res.status_code, 200)
        sell1_data = json.loads(sell1_res.data)
        self.assertTrue(sell1_data["success"])
        self.assertEqual(sell1_data["realized_pnl"], 1985.0)
        self.assertEqual(sell1_data["remaining_qty"], 15)

        # 10. Check Portfolio Summary after partial SELL
        sum2_res = self.client.get("/api/portfolio/summary")
        sum2_data = json.loads(sum2_res.data)["data"]
        # Remaining invested = (15 * 3600) + (5 * 2800) = 54000 + 14000 = 68000.0
        self.assertEqual(sum2_data["total_invested"], 68000.0)
        self.assertEqual(sum2_data["realized_pnl"], 1985.0)

        # 11. Full SELL: Sell remaining 5 RELIANCE.NS @ ₹2,900 with ₹10 fee
        # Realized P&L = (2900 - 2800) * 5 - 10 = 500 - 10 = 490.0
        sell2_res = self.client.post(
            "/api/portfolio/sell",
            json={
                "symbol": "RELIANCE.NS",
                "quantity": 5,
                "price": 2900.0,
                "fees": 10.0,
                "notes": "Full exit",
            },
        )
        self.assertEqual(sell2_res.status_code, 200)
        sell2_data = json.loads(sell2_res.data)
        self.assertTrue(sell2_data["success"])
        self.assertEqual(sell2_data["realized_pnl"], 490.0)
        self.assertEqual(sell2_data["remaining_qty"], 0)

        # 12. Check Transactions Log API
        txns_res = self.client.get("/api/portfolio/transactions")
        self.assertEqual(txns_res.status_code, 200)
        txns = json.loads(txns_res.data)["transactions"]
        self.assertEqual(len(txns), 5)  # 3 BUYs + 2 SELLs

        # 13. AI Portfolio Analysis API
        ai_port_res = self.client.post("/api/portfolio/analyze-ai")
        self.assertEqual(ai_port_res.status_code, 200)
        ai_port_data = json.loads(ai_port_res.data)
        self.assertTrue(ai_port_data["success"])
        self.assertIn("summary", ai_port_data)
        self.assertGreater(len(ai_port_data["strengths"]), 0)

        # 14. Watchlist Add & Remove
        add_w_res = self.client.post(
            "/watchlist/add",
            data={"symbol": "INFY.NS"},
        )
        self.assertEqual(add_w_res.status_code, 200)
        rem_w_res = self.client.post(
            "/watchlist/remove",
            data={"symbol": "INFY.NS"},
        )
        self.assertEqual(rem_w_res.status_code, 200)

        # 15. Stock Analysis Page
        analysis_res = self.client.get("/analysis?symbol=TCS.NS")
        self.assertEqual(analysis_res.status_code, 200)
        self.assertIn(b"Tata Consultancy", analysis_res.data)

        # 16. Compare Page
        comp_res = self.client.get("/compare?stock1=TCS.NS&stock2=INFY.NS")
        self.assertEqual(comp_res.status_code, 200)

        # 17. AI Assistant Chatbot with Portfolio Context Tool
        chat_res = self.client.post(
            "/api/ask-ai",
            json={"question": "What is my current portfolio invested capital?"},
        )
        chat_data = json.loads(chat_res.data)
        self.assertIn("answer", chat_data)

        # 18. Logout
        logout_res = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(logout_res.status_code, 200)
        self.assertIn(b"Log In", logout_res.data)

    # -------------------------------------------------------------
    # 3. EXTERNAL DATA FAILURE & GRACEFUL DEGRADATION TESTS
    # -------------------------------------------------------------
    def test_missing_and_failed_external_data_graceful_handling(self):
        """Verify the system degrades gracefully and never crashes or fabricates fake data on missing inputs."""
        # 1. Fundamental Service missing data handling
        empty_fundamentals = FundamentalService.extract_fundamentals(None)
        self.assertFalse(empty_fundamentals["available"])
        self.assertIn("not available", empty_fundamentals["reason"].lower())

        # 2. Technical Service empty DataFrame handling
        import pandas as pd

        empty_technicals = TechnicalService.calculate_indicators(pd.DataFrame())
        self.assertFalse(empty_technicals["available"])
        self.assertIn("unavailable", empty_technicals["reason"].lower())

        # 3. Target Service when technicals are missing
        targets = TargetService.calculate_targets(100.0, {"available": False})
        self.assertFalse(targets["available"])
        self.assertEqual(targets["target_price"], "Not available")
        self.assertEqual(targets["stop_loss"], "Not available")

        # 4. News Service empty news handling
        score = NewsService.get_sentiment_score([])
        self.assertEqual(score, 50)

        # 5. Scoring Engine when external data is missing
        score_res = ScoringEngine.evaluate_stock(
            fundamentals_data={"available": False},
            technicals_data={"available": False},
            news_sentiment_score=50,
        )
        self.assertIn(score_res["signal"], ["Hold", "Reduce", "Neutral"])
        self.assertIn("factor_scores", score_res)
        self.assertIn("confidence", score_res)


if __name__ == "__main__":
    unittest.main()
