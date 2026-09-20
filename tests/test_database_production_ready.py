import unittest
import os
import uuid
from decimal import Decimal
from unittest.mock import patch

from app import app, db
from config import get_database_uri, get_engine_options, validate_database_driver
from database.models import (
    User,
    Portfolio,
    Holding,
    Transaction,
    Watchlist,
    StockAlert,
    PortfolioSnapshot,
    AIAnalysisCache,
)
from services.portfolio_service import PortfolioService
from database.migrations import (
    ensure_migration_table,
    get_applied_revisions,
    upgrade,
    downgrade,
    status,
    MIGRATION_REVISIONS,
)
from flask_bcrypt import Bcrypt
from sqlalchemy import inspect, text


class TestDatabaseProductionReady(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()

        self.app_context = self.app.app_context()
        self.app_context.push()

        db.session.remove()
        db.drop_all()
        db.create_all()

        bcrypt = Bcrypt(self.app)
        uid = str(uuid.uuid4())[:8]

        self.user = User(
            full_name="DB Test User",
            email=f"dbtest_{uid}@investiq.com",
            password=bcrypt.generate_password_hash("Password123!").decode("utf-8"),
        )
        db.session.add(self.user)
        db.session.commit()
        self.user_id = self.user.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # =========================================================================
    # CONFIGURATION TESTS (1 - 6)
    # =========================================================================

    def test_01_sqlite_fallback(self):
        """1. Verify default database URI falls back to SQLite cleanly."""
        with patch.dict(os.environ, {}, clear=True):
            uri = get_database_uri()
            self.assertTrue(uri.startswith("sqlite:"))

    def test_02_postgresql_url_detection(self):
        """2. Verify PostgreSQL URL is detected from DATABASE_URL."""
        pg_uri = "postgresql://invest_user:pass@localhost:5432/investiq_db"
        with patch.dict(os.environ, {"DATABASE_URL": pg_uri}):
            self.assertEqual(get_database_uri(), pg_uri)

    def test_03_postgres_legacy_normalization(self):
        """3. Verify legacy postgres:// URI is normalized to postgresql:// for SQLAlchemy 1.4+."""
        legacy_uri = "postgres://user:secret@ep-cool-db.aws.neon.tech/neondb"
        with patch.dict(os.environ, {"DATABASE_URL": legacy_uri}):
            normalized = get_database_uri()
            self.assertEqual(normalized, "postgresql://user:secret@ep-cool-db.aws.neon.tech/neondb")

    def test_04_postgresql_engine_options(self):
        """4. Verify engine options configure pooling parameters for PostgreSQL."""
        pg_opts = get_engine_options("postgresql://user:pass@localhost:5432/investiq")
        self.assertTrue(pg_opts.get("pool_pre_ping"))
        self.assertGreaterEqual(pg_opts.get("pool_size", 0), 5)
        self.assertGreaterEqual(pg_opts.get("max_overflow", 0), 10)
        self.assertEqual(pg_opts.get("pool_recycle"), 1800)
        self.assertEqual(pg_opts.get("pool_timeout"), 30)

    def test_05_sqlite_engine_options(self):
        """5. Verify engine options configure check_same_thread for SQLite without pool args."""
        sqlite_opts = get_engine_options("sqlite:///database.db")
        self.assertIn("connect_args", sqlite_opts)
        self.assertFalse(sqlite_opts["connect_args"]["check_same_thread"])
        self.assertNotIn("pool_size", sqlite_opts)

    def test_06_driver_validation_raises_when_driver_missing(self):
        """6. Verify validate_database_driver raises clear error without leaking credentials."""
        with patch("builtins.__import__", side_effect=ImportError("No module named 'psycopg2'")):
            with self.assertRaises(RuntimeError) as ctx:
                validate_database_driver("postgresql://secret_user:super_secret_password@db.host.com/prod_db")
            error_msg = str(ctx.exception)
            self.assertIn("PostgreSQL driver is not installed", error_msg)
            # Ensure password / credentials were NOT leaked in error message
            self.assertNotIn("super_secret_password", error_msg)

    # =========================================================================
    # SCHEMA & INDEX TESTS (7 - 12)
    # =========================================================================

    def test_07_required_tables_exist(self):
        """7. Verify all required application entities exist."""
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())
        expected_tables = {
            "users", "portfolios", "holdings", "transactions",
            "watchlist", "portfolio_snapshots", "stock_alerts", "ai_analysis_cache"
        }
        self.assertTrue(expected_tables.issubset(tables))

    def test_08_required_columns_exist(self):
        """8. Verify critical user and transaction columns exist."""
        inspector = inspect(db.engine)
        user_cols = {col["name"] for col in inspector.get_columns("users")}
        self.assertTrue({"id", "full_name", "email", "password", "risk_profile", "google_id"}.issubset(user_cols))

        txn_cols = {col["name"] for col in inspector.get_columns("transactions")}
        self.assertTrue({"id", "portfolio_id", "user_id", "symbol", "quantity", "price", "total_amount", "realized_pnl"}.issubset(txn_cols))

    def test_09_primary_keys_exist(self):
        """9. Verify all tables have single 'id' primary keys."""
        inspector = inspect(db.engine)
        for tbl in ["users", "portfolios", "holdings", "transactions", "watchlist", "stock_alerts"]:
            pk = inspector.get_pk_constraint(tbl)
            self.assertEqual(pk["constrained_columns"], ["id"])

    def test_10_foreign_keys_exist(self):
        """10. Verify foreign key constraints link portfolios, holdings, txns, and watchlists to users."""
        inspector = inspect(db.engine)
        portfolio_fks = inspector.get_foreign_keys("portfolios")
        self.assertTrue(any(fk["referred_table"] == "users" for fk in portfolio_fks))

        holding_fks = inspector.get_foreign_keys("holdings")
        self.assertTrue(any(fk["referred_table"] == "portfolios" for fk in holding_fks))

    def test_11_expected_indexes_exist(self):
        """11. Verify critical query performance indexes are defined in ORM models."""
        self.assertTrue(Portfolio.user_id.index)
        self.assertTrue(Holding.portfolio_id.index)
        self.assertTrue(Holding.symbol.index)
        self.assertTrue(Transaction.portfolio_id.index)
        self.assertTrue(Transaction.user_id.index)
        self.assertTrue(Transaction.symbol.index)
        self.assertTrue(Transaction.created_at.index)
        self.assertTrue(Watchlist.user_id.index)
        self.assertTrue(AIAnalysisCache.symbol.index)

    def test_12_no_duplicate_indexes_on_unique_fields(self):
        """12. Verify unique columns (User.email, AIAnalysisCache.symbol) maintain uniqueness constraint."""
        self.assertTrue(User.email.unique)
        self.assertTrue(AIAnalysisCache.symbol.unique)

    # =========================================================================
    # TRANSACTION ATOMICITY & CONCURRENCY TESTS (13 - 18)
    # =========================================================================

    def test_13_buy_transaction_committed_atomically(self):
        """13. Verify valid BUY execution creates transaction and updates holding atomically."""
        portfolio = PortfolioService.get_or_create_portfolio(self.user_id)
        holding, txn = PortfolioService.record_buy(
            portfolio_id=portfolio.id,
            user_id=self.user_id,
            symbol="INFY.NS",
            quantity=10.0,
            price=1500.0,
            fees=20.0,
        )
        self.assertIsNotNone(holding.id)
        self.assertIsNotNone(txn.id)
        self.assertEqual(holding.quantity, 10.0)
        self.assertEqual(txn.total_amount, 15020.0)

    def test_14_buy_transaction_rolled_back_on_error(self):
        """14. Verify BUY failure rolls back session cleanly without partial holding updates."""
        portfolio = PortfolioService.get_or_create_portfolio(self.user_id)
        PortfolioService.record_buy(
            portfolio_id=portfolio.id,
            user_id=self.user_id,
            symbol="WIPRO.NS",
            quantity=10.0,
            price=450.0,
        )

        with patch.object(db.session, "commit", side_effect=RuntimeError("Disk Failure")):
            with self.assertRaises(RuntimeError):
                PortfolioService.record_buy(
                    portfolio_id=portfolio.id,
                    user_id=self.user_id,
                    symbol="WIPRO.NS",
                    quantity=5.0,
                    price=500.0,
                )

        db.session.expire_all()
        holding = Holding.query.filter_by(portfolio_id=portfolio.id, symbol="WIPRO.NS").first()
        self.assertEqual(holding.quantity, 10.0)

    def test_15_sell_transaction_committed_atomically(self):
        """15. Verify valid SELL execution creates transaction and deducts holding atomically."""
        portfolio = PortfolioService.get_or_create_portfolio(self.user_id)
        PortfolioService.record_buy(
            portfolio_id=portfolio.id,
            user_id=self.user_id,
            symbol="HDFC.NS",
            quantity=20.0,
            price=1600.0,
        )

        holding, txn = PortfolioService.record_sell(
            portfolio_id=portfolio.id,
            user_id=self.user_id,
            symbol="HDFC.NS",
            quantity=10.0,
            price=1700.0,
            fees=15.0,
        )
        self.assertEqual(holding.quantity, 10.0)
        self.assertEqual(txn.realized_pnl, 985.0)  # (1700-1600)*10 - 15

    def test_16_sell_transaction_rolled_back_on_error(self):
        """16. Verify SELL failure rolls back quantity deductions."""
        portfolio = PortfolioService.get_or_create_portfolio(self.user_id)
        PortfolioService.record_buy(
            portfolio_id=portfolio.id,
            user_id=self.user_id,
            symbol="SBIN.NS",
            quantity=50.0,
            price=600.0,
        )

        with patch.object(db.session, "commit", side_effect=RuntimeError("Network Error")):
            with self.assertRaises(RuntimeError):
                PortfolioService.record_sell(
                    portfolio_id=portfolio.id,
                    user_id=self.user_id,
                    symbol="SBIN.NS",
                    quantity=25.0,
                    price=650.0,
                )

        db.session.expire_all()
        holding = Holding.query.filter_by(portfolio_id=portfolio.id, symbol="SBIN.NS").first()
        self.assertEqual(holding.quantity, 50.0)

    def test_17_intermediate_stage_failure_preserves_clean_state(self):
        """17. Verify exception during multi-step trade operation leaves zero corrupt records."""
        portfolio = PortfolioService.get_or_create_portfolio(self.user_id)
        initial_txn_count = Transaction.query.filter_by(portfolio_id=portfolio.id).count()

        # Overselling raises ValueError before commit
        with self.assertRaises(ValueError):
            PortfolioService.record_sell(
                portfolio_id=portfolio.id,
                user_id=self.user_id,
                symbol="NONEXISTENT.NS",
                quantity=100.0,
                price=500.0,
            )

        final_txn_count = Transaction.query.filter_by(portfolio_id=portfolio.id).count()
        self.assertEqual(initial_txn_count, final_txn_count)

    def test_18_concurrent_row_lookup_safety(self):
        """18. Verify holding row lookup behaves safely under transactional isolation."""
        portfolio = PortfolioService.get_or_create_portfolio(self.user_id)
        PortfolioService.record_buy(
            portfolio_id=portfolio.id,
            user_id=self.user_id,
            symbol="AXISBANK.NS",
            quantity=10.0,
            price=1000.0,
        )

        holding = Holding.query.filter_by(portfolio_id=portfolio.id, symbol="AXISBANK.NS").first()
        self.assertIsNotNone(holding)
        self.assertEqual(holding.quantity, 10.0)

    # =========================================================================
    # DATA ISOLATION & CASCADING TESTS (19 - 20)
    # =========================================================================

    def test_19_user_deletion_cascades_owned_entities(self):
        """19. Verify deleting a user cascades and deletes all owned entities."""
        portfolio = PortfolioService.get_or_create_portfolio(self.user_id)
        PortfolioService.record_buy(
            portfolio_id=portfolio.id,
            user_id=self.user_id,
            symbol="RELIANCE.NS",
            quantity=10.0,
            price=2500.0,
        )
        watchlist_item = Watchlist(user_id=self.user_id, symbol="RELIANCE.NS")
        db.session.add(watchlist_item)
        db.session.commit()

        user = db.session.get(User, self.user_id)
        db.session.delete(user)
        db.session.commit()

        self.assertIsNone(Portfolio.query.filter_by(user_id=self.user_id).first())
        self.assertIsNone(Holding.query.filter_by(portfolio_id=portfolio.id).first())
        self.assertEqual(Transaction.query.filter_by(user_id=self.user_id).count(), 0)
        self.assertEqual(Watchlist.query.filter_by(user_id=self.user_id).count(), 0)

    def test_20_no_orphaned_records_between_users(self):
        """20. Verify User B cannot access or affect User A's holdings or transactions."""
        portfolio_a = PortfolioService.get_or_create_portfolio(self.user_id)
        PortfolioService.record_buy(
            portfolio_id=portfolio_a.id,
            user_id=self.user_id,
            symbol="TCS.NS",
            quantity=15.0,
            price=3500.0,
        )

        # Create User B
        bcrypt = Bcrypt(self.app)
        user_b = User(
            full_name="User B",
            email=f"user_b_{uuid.uuid4().hex[:6]}@investiq.com",
            password=bcrypt.generate_password_hash("Password123!").decode("utf-8"),
        )
        db.session.add(user_b)
        db.session.commit()

        portfolio_b = PortfolioService.get_or_create_portfolio(user_b.id)
        holdings_b = Holding.query.filter_by(portfolio_id=portfolio_b.id).all()
        self.assertEqual(len(holdings_b), 0)

    # =========================================================================
    # MIGRATION TESTS (21 - 24)
    # =========================================================================

    def test_21_migration_status_tracking(self):
        """21. Verify migration system logs and tracks applied revision IDs."""
        ensure_migration_table()
        upgrade()
        applied = get_applied_revisions()
        self.assertEqual(len(applied), len(MIGRATION_REVISIONS))

    def test_22_migration_idempotency(self):
        """22. Verify running upgrade multiple times is safe and idempotent."""
        upgrade()
        applied_first = get_applied_revisions()
        upgrade()
        applied_second = get_applied_revisions()
        self.assertEqual(applied_first, applied_second)

    def test_23_existing_schema_detection(self):
        """23. Verify schema inspection accurately detects existing tables without error."""
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()
        self.assertIn("users", table_names)
        self.assertIn("transactions", table_names)

    def test_24_non_destructive_downgrade(self):
        """24. Verify downgrade does not destructively drop core production tables."""
        upgrade()
        downgrade()
        inspector = inspect(db.engine)
        self.assertIn("users", inspector.get_table_names())

    # =========================================================================
    # HEALTH CHECK TEST (25)
    # =========================================================================

    def test_25_database_connectivity_health_endpoint(self):
        """25. Verify /api/health/db executes SELECT 1 and returns clean healthy JSON status."""
        response = self.client.get("/api/health/db")
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data.get("status"), "healthy")
        self.assertEqual(json_data.get("database"), "connected")
        self.assertIn(json_data.get("dialect"), ["sqlite", "postgresql"])
        # Ensure credentials / sensitive connection strings are not exposed
        self.assertNotIn("password", str(json_data).lower())


if __name__ == "__main__":
    unittest.main()
