import unittest
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from database.models import User, Portfolio, Holding, Transaction
from services.portfolio_service import PortfolioService
from flask_bcrypt import Bcrypt


class TestApiAndRoutes(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.bcrypt = Bcrypt(app)
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

        # Clean existing test user if present
        existing = User.query.filter_by(email="integration@example.com").first()
        if existing:
            for p in Portfolio.query.filter_by(user_id=existing.id).all():
                Holding.query.filter_by(portfolio_id=p.id).delete()
                Transaction.query.filter_by(portfolio_id=p.id).delete()
                db.session.delete(p)
            db.session.delete(existing)
            db.session.commit()

        # Create user
        hashed = self.bcrypt.generate_password_hash("password123").decode("utf-8")
        self.user = User(
            full_name="Integration User",
            email="integration@example.com",
            password=hashed,
        )
        db.session.add(self.user)
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        try:
            existing = User.query.filter_by(email="integration@example.com").first()
            if existing:
                for p in Portfolio.query.filter_by(user_id=existing.id).all():
                    Holding.query.filter_by(portfolio_id=p.id).delete()
                    Transaction.query.filter_by(portfolio_id=p.id).delete()
                    db.session.delete(p)
                db.session.delete(existing)
                db.session.commit()
        except Exception:
            db.session.rollback()
        finally:
            db.session.remove()
            self.app_context.pop()

    def login_client(self):
        return self.client.post(
            "/login",
            data={"email": "integration@example.com", "password": "password123"},
            follow_redirects=True,
        )

    def test_unauthenticated_redirects(self):
        # Protected endpoints redirect to login
        res = self.client.get("/dashboard")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers["Location"])

        res = self.client.get("/portfolio")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers["Location"])

    def test_authenticated_page_routes(self):
        self.login_client()

        # 1. Dashboard
        res = self.client.get("/dashboard")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Portfolio Value", res.data)

        # 2. Portfolio Page
        res = self.client.get("/portfolio")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Investment Portfolio", res.data)
        self.assertIn(b"Holdings", res.data)

        # 3. Watchlist
        res = self.client.get("/watchlist")
        self.assertEqual(res.status_code, 200)

        # 4. Analysis
        res = self.client.get("/analysis")
        self.assertEqual(res.status_code, 200)

        # 5. Compare
        res = self.client.get("/compare")
        self.assertEqual(res.status_code, 200)

    def test_search_stocks_api(self):
        self.login_client()
        res = self.client.get("/api/search-stocks?q=TCS")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        self.assertIn("symbol", data[0])

    def test_portfolio_buy_and_sell_api_flow(self):
        self.login_client()

        # Clean state for user portfolio
        p = PortfolioService.get_or_create_portfolio(self.user.id)
        Holding.query.filter_by(portfolio_id=p.id).delete()
        Transaction.query.filter_by(portfolio_id=p.id).delete()
        db.session.commit()

        # 1. Record BUY via API
        buy_payload = {
            "symbol": "TCS.NS",
            "quantity": 10,
            "price": 3800.0,
            "fees": 15.0,
            "notes": "API test buy",
        }
        res = self.client.post(
            "/api/portfolio/buy",
            json=buy_payload,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res.status_code, 200)
        buy_data = json.loads(res.data)
        self.assertTrue(buy_data["success"])
        self.assertEqual(buy_data["holding"]["quantity"], 10)
        self.assertEqual(buy_data["holding"]["avg_price"], 3800.0)

        # 2. Check Summary API
        res = self.client.get("/api/portfolio/summary")
        self.assertEqual(res.status_code, 200)
        sum_data = json.loads(res.data)["data"]
        self.assertTrue(sum_data["has_holdings"])
        self.assertEqual(sum_data["total_invested"], 38000.0)
        self.assertEqual(sum_data["holdings_count"], 1)

        # 3. Record SELL via API
        sell_payload = {
            "symbol": "TCS.NS",
            "quantity": 4,
            "price": 4000.0,
            "fees": 10.0,
            "notes": "API test sell",
        }
        res = self.client.post(
            "/api/portfolio/sell",
            json=sell_payload,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res.status_code, 200)
        sell_data = json.loads(res.data)
        self.assertTrue(sell_data["success"])
        # Realized P&L = (4000 - 3800) * 4 - 10 = 790
        self.assertEqual(sell_data["realized_pnl"], 790.0)

        # 4. Check Transactions API
        res = self.client.get("/api/portfolio/transactions")
        self.assertEqual(res.status_code, 200)
        txns = json.loads(res.data)["transactions"]
        self.assertEqual(len(txns), 2)
        self.assertEqual(txns[0]["type"], "SELL")
        self.assertEqual(txns[1]["type"], "BUY")


if __name__ == "__main__":
    unittest.main()
