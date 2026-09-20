import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from database.models import User, Portfolio, Holding, Transaction
from services.portfolio_service import PortfolioService


class TestPortfolioSystem(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

        # Clean existing test users if any
        existing = User.query.filter_by(email="test_investor@example.com").first()
        if existing:
            for p in Portfolio.query.filter_by(user_id=existing.id).all():
                Holding.query.filter_by(portfolio_id=p.id).delete()
                Transaction.query.filter_by(portfolio_id=p.id).delete()
                db.session.delete(p)
            db.session.delete(existing)
            db.session.commit()

        test_user = User(
            full_name="Test Investor",
            email="test_investor@example.com",
            password="hashed_password",
        )
        db.session.add(test_user)
        db.session.commit()
        self.user_id = test_user.id

    def tearDown(self):
        try:
            if hasattr(self, "user_id"):
                for p in Portfolio.query.filter_by(user_id=self.user_id).all():
                    Holding.query.filter_by(portfolio_id=p.id).delete()
                    Transaction.query.filter_by(portfolio_id=p.id).delete()
                    db.session.delete(p)
                User.query.filter_by(id=self.user_id).delete()
                db.session.commit()
        except Exception:
            db.session.rollback()
        finally:
            db.session.remove()
            self.app_context.pop()

    def test_portfolio_creation(self):
        portfolio = PortfolioService.get_or_create_portfolio(self.user_id)
        self.assertIsNotNone(portfolio)
        self.assertEqual(portfolio.user_id, self.user_id)
        self.assertEqual(portfolio.name, "Primary Portfolio")

    def test_buy_transaction_and_weighted_average(self):
        portfolio = PortfolioService.get_or_create_portfolio(self.user_id)

        # 1. Buy 10 shares of RELIANCE.NS @ ₹2,800
        holding1, txn1 = PortfolioService.record_buy(
            portfolio_id=portfolio.id,
            user_id=self.user_id,
            symbol="RELIANCE.NS",
            quantity=10,
            price=2800.0,
            fees=20.0,
            notes="First tranche",
        )
        self.assertEqual(holding1.quantity, 10)
        self.assertEqual(holding1.average_buy_price, 2800.0)
        self.assertEqual(txn1.transaction_type, "BUY")
        self.assertEqual(txn1.total_amount, 28020.0)

        # 2. Buy 10 more shares of RELIANCE.NS @ ₹3,000
        # Weighted Average: (10*2800 + 10*3000)/20 = 2900.0
        holding2, txn2 = PortfolioService.record_buy(
            portfolio_id=portfolio.id,
            user_id=self.user_id,
            symbol="RELIANCE.NS",
            quantity=10,
            price=3000.0,
            fees=20.0,
            notes="Second tranche",
        )
        self.assertEqual(holding2.quantity, 20)
        self.assertEqual(holding2.average_buy_price, 2900.0)

        # 3. Buy 5 more shares @ ₹3,200
        # Weighted Average: (20*2900 + 5*3200)/25 = (58000 + 16000)/25 = 74000/25 = 2960.0
        holding3, _ = PortfolioService.record_buy(
            portfolio_id=portfolio.id,
            user_id=self.user_id,
            symbol="RELIANCE.NS",
            quantity=5,
            price=3200.0,
        )
        self.assertEqual(holding3.quantity, 25)
        self.assertEqual(holding3.average_buy_price, 2960.0)

    def test_partial_sell_and_realized_pnl(self):
        portfolio = PortfolioService.get_or_create_portfolio(self.user_id)

        # Buy 20 shares @ ₹1,000
        PortfolioService.record_buy(
            portfolio_id=portfolio.id,
            user_id=self.user_id,
            symbol="TCS.NS",
            quantity=20,
            price=1000.0,
        )

        # Sell 5 shares @ ₹1,200 with ₹10 fees
        # Realized P&L = (1200 - 1000) * 5 - 10 = +990
        holding, txn = PortfolioService.record_sell(
            portfolio_id=portfolio.id,
            user_id=self.user_id,
            symbol="TCS.NS",
            quantity=5,
            price=1200.0,
            fees=10.0,
            notes="Profit booking",
        )

        self.assertEqual(holding.quantity, 15)
        self.assertEqual(holding.average_buy_price, 1000.0)
        self.assertEqual(txn.realized_pnl, 990.0)
        self.assertEqual(txn.transaction_type, "SELL")

    def test_overselling_raises_error(self):
        portfolio = PortfolioService.get_or_create_portfolio(self.user_id)

        PortfolioService.record_buy(
            portfolio_id=portfolio.id,
            user_id=self.user_id,
            symbol="INFY.NS",
            quantity=5,
            price=1500.0,
        )

        with self.assertRaises(ValueError) as ctx:
            PortfolioService.record_sell(
                portfolio_id=portfolio.id,
                user_id=self.user_id,
                symbol="INFY.NS",
                quantity=10,
                price=1600.0,
            )
        self.assertIn("Insufficient shares", str(ctx.exception))

    def test_complete_sell_removes_holding(self):
        portfolio = PortfolioService.get_or_create_portfolio(self.user_id)

        PortfolioService.record_buy(
            portfolio_id=portfolio.id,
            user_id=self.user_id,
            symbol="SBIN.NS",
            quantity=10,
            price=800.0,
        )

        PortfolioService.record_sell(
            portfolio_id=portfolio.id,
            user_id=self.user_id,
            symbol="SBIN.NS",
            quantity=10,
            price=850.0,
        )

        remaining = Holding.query.filter_by(
            portfolio_id=portfolio.id, symbol="SBIN.NS"
        ).first()
        self.assertIsNone(remaining)

        txns = Transaction.query.filter_by(
            portfolio_id=portfolio.id, symbol="SBIN.NS"
        ).all()
        self.assertEqual(len(txns), 2)

    def test_portfolio_summary_calculations(self):
        portfolio = PortfolioService.get_or_create_portfolio(self.user_id)

        PortfolioService.record_buy(
            portfolio_id=portfolio.id,
            user_id=self.user_id,
            symbol="RELIANCE.NS",
            quantity=10,
            price=3000.0,
        )
        PortfolioService.record_buy(
            portfolio_id=portfolio.id,
            user_id=self.user_id,
            symbol="TCS.NS",
            quantity=10,
            price=3500.0,
        )

        summary = PortfolioService.get_portfolio_summary(portfolio.id)
        self.assertTrue(summary["has_holdings"])
        self.assertEqual(summary["total_invested"], 65000.0)
        self.assertEqual(summary["holdings_count"], 2)
        self.assertIsNotNone(summary["health_score"])
        self.assertTrue(0 <= summary["health_score"] <= 100)


if __name__ == "__main__":
    unittest.main()
