"""Production-Ready Versioned Database Migration Engine.

Supports both SQLite (local development) and PostgreSQL (production).
Provides revision tracking, idempotent upgrade, safe downgrade, current revision check,
migration history, and schema inspection without external dependencies.
"""

import sys
import os
from datetime import datetime, timezone
from sqlalchemy import inspect, text

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app
from database.models import db


# =============================================================================
# REVISION DEFINITIONS
# =============================================================================

MIGRATION_REVISIONS = [
    {
        "revision": "001_initial_schema",
        "description": "Create base tables: users, portfolios, holdings, transactions, watchlist, portfolio_snapshots, stock_alerts, ai_analysis_cache",
        "upgrade_func": "upgrade_001",
        "downgrade_func": "downgrade_001",
    },
    {
        "revision": "002_user_profile_and_auth",
        "description": "Add user profile columns: phone, risk_profile, investment_goal, preferred_market, google_id, auth_provider",
        "upgrade_func": "upgrade_002",
        "downgrade_func": "downgrade_002",
    },
    {
        "revision": "003_production_indexes",
        "description": "Create query performance indexes across high-traffic foreign keys and timestamp columns",
        "upgrade_func": "upgrade_003",
        "downgrade_func": "downgrade_003",
    },
]


def ensure_migration_table():
    """Ensure the schema_version tracking table exists."""
    with app.app_context():
        db.session.execute(
            text(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "  revision VARCHAR(64) PRIMARY KEY,"
                "  description VARCHAR(255) NOT NULL,"
                "  applied_at TIMESTAMP NOT NULL"
                ")"
            )
        )
        db.session.commit()


def get_applied_revisions() -> set:
    """Return set of applied revision IDs."""
    ensure_migration_table()
    with app.app_context():
        rows = db.session.execute(text("SELECT revision FROM schema_migrations")).fetchall()
        return {r[0] for r in rows}


def record_migration_applied(revision: str, description: str):
    """Log an applied migration revision."""
    with app.app_context():
        db.session.execute(
            text("INSERT INTO schema_migrations (revision, description, applied_at) VALUES (:rev, :desc, :ts)"),
            {"rev": revision, "desc": description, "ts": datetime.now(timezone.utc)},
        )
        db.session.commit()


def remove_migration_record(revision: str):
    """Remove a migration record upon rollback/downgrade."""
    with app.app_context():
        db.session.execute(
            text("DELETE FROM schema_migrations WHERE revision = :rev"),
            {"rev": revision},
        )
        db.session.commit()


# =============================================================================
# INDIVIDUAL MIGRATION HANDLERS
# =============================================================================

def upgrade_001():
    """Revision 001: Base schema creation."""
    db.create_all()


def downgrade_001():
    """Revision 001 downgrade: Non-destructive notice in production."""
    print("[-] Downgrade 001: Core base tables retained to prevent data loss.")


def upgrade_002():
    """Revision 002: Add extended user columns."""
    inspector = inspect(db.engine)
    if "users" in inspector.get_table_names():
        existing_cols = {c["name"] for c in inspector.get_columns("users")}
        columns_to_add = [
            ("phone", "VARCHAR(25)"),
            ("risk_profile", "VARCHAR(30) DEFAULT 'Moderate' NOT NULL"),
            ("investment_goal", "VARCHAR(120)"),
            ("preferred_market", "VARCHAR(30) DEFAULT 'NSE' NOT NULL"),
            ("google_id", "VARCHAR(255)"),
            ("auth_provider", "VARCHAR(30) DEFAULT 'email' NOT NULL"),
        ]
        for col_name, col_def in columns_to_add:
            if col_name not in existing_cols:
                db.session.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"))
                db.session.commit()
                existing_cols.add(col_name)

        db.session.execute(
            text("UPDATE users SET auth_provider = 'email' WHERE auth_provider IS NULL OR auth_provider = ''")
        )
        db.session.commit()


def downgrade_002():
    """Revision 002 downgrade: Safe non-destructive column retain."""
    print("[-] Downgrade 002: User columns retained safely.")


def upgrade_003():
    """Revision 003: Create production indexes."""
    indexes_to_create = [
        ("ix_users_google_id", "users", "google_id"),
        ("ix_portfolios_user_id", "portfolios", "user_id"),
        ("ix_holdings_portfolio_id", "holdings", "portfolio_id"),
        ("ix_holdings_symbol", "holdings", "symbol"),
        ("ix_transactions_portfolio_id", "transactions", "portfolio_id"),
        ("ix_transactions_user_id", "transactions", "user_id"),
        ("ix_transactions_symbol", "transactions", "symbol"),
        ("ix_transactions_created_at", "transactions", "created_at"),
        ("ix_watchlist_user_id", "watchlist", "user_id"),
        ("ix_watchlist_symbol", "watchlist", "symbol"),
        ("ix_snapshots_portfolio_id", "portfolio_snapshots", "portfolio_id"),
        ("ix_snapshots_date", "portfolio_snapshots", "snapshot_date"),
        ("ix_alerts_user_id", "stock_alerts", "user_id"),
        ("ix_alerts_symbol", "stock_alerts", "symbol"),
        ("ix_ai_cache_expires_at", "ai_analysis_cache", "expires_at"),
    ]
    for idx_name, tbl_name, col_name in indexes_to_create:
        try:
            db.session.execute(
                text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {tbl_name}({col_name})")
            )
            db.session.commit()
        except Exception:
            db.session.rollback()


def downgrade_003():
    """Revision 003 downgrade: Drop non-critical indexes."""
    indexes_to_drop = [
        "ix_portfolios_user_id", "ix_holdings_portfolio_id", "ix_holdings_symbol",
        "ix_transactions_portfolio_id", "ix_transactions_user_id", "ix_transactions_symbol",
        "ix_transactions_created_at", "ix_watchlist_user_id", "ix_watchlist_symbol"
    ]
    for idx in indexes_to_drop:
        try:
            db.session.execute(text(f"DROP INDEX IF EXISTS {idx}"))
            db.session.commit()
        except Exception:
            db.session.rollback()


# =============================================================================
# CLI COMMANDS (UPGRADE, DOWNGRADE, CURRENT, HISTORY, STATUS)
# =============================================================================

def upgrade():
    """Apply all pending migration revisions in sequence."""
    ensure_migration_table()
    with app.app_context():
        applied = get_applied_revisions()
        print(f"[*] Upgrading database dialect: {db.engine.dialect.name}...")

        for rev_dict in MIGRATION_REVISIONS:
            rev_id = rev_dict["revision"]
            if rev_id not in applied:
                print(f"[+] Applying revision {rev_id}: {rev_dict['description']}...")
                handler = globals()[rev_dict["upgrade_func"]]
                handler()
                record_migration_applied(rev_id, rev_dict["description"])
                print(f"[OK] Successfully applied {rev_id}")
            else:
                print(f"[-] Revision {rev_id} already applied (skipping).")

        print("\n[OK] Database is up to date!")


def downgrade():
    """Roll back the most recent migration revision."""
    ensure_migration_table()
    with app.app_context():
        applied = get_applied_revisions()
        for rev_dict in reversed(MIGRATION_REVISIONS):
            rev_id = rev_dict["revision"]
            if rev_id in applied:
                print(f"[-] Downgrading revision {rev_id}: {rev_dict['description']}...")
                handler = globals()[rev_dict["downgrade_func"]]
                handler()
                remove_migration_record(rev_id)
                print(f"[OK] Successfully rolled back {rev_id}")
                return
        print("[!] No applied revisions to downgrade.")


def current():
    """Display the currently applied revision."""
    ensure_migration_table()
    with app.app_context():
        rows = db.session.execute(
            text("SELECT revision, description, applied_at FROM schema_migrations ORDER BY applied_at DESC")
        ).fetchall()
        if rows:
            latest = rows[0]
            print(f"\nCurrent Revision: {latest[0]}")
            print(f"Description:      {latest[1]}")
            print(f"Applied At:       {latest[2]}\n")
        else:
            print("\nNo migrations have been applied yet.\n")


def history():
    """Display the complete history of applied revisions."""
    ensure_migration_table()
    with app.app_context():
        rows = db.session.execute(
            text("SELECT revision, description, applied_at FROM schema_migrations ORDER BY applied_at ASC")
        ).fetchall()
        print("\n=== Migration History ===")
        if not rows:
            print("  (No migration history found)")
        for r in rows:
            print(f"  [{r[2]}] {r[0]:<30} - {r[1]}")
        print("=========================\n")


def status():
    """Inspect and report database dialect, connection pool, tables, and migration state."""
    ensure_migration_table()
    with app.app_context():
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        applied = get_applied_revisions()

        print("\n=== Stratix AI Database Status ===")
        print(f"Dialect:              {db.engine.dialect.name}")
        print(f"Target URI:           {app.config['SQLALCHEMY_DATABASE_URI']}")
        print(f"Engine Options:       {app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {})}")
        print(f"Total Tables:         {len(tables)}")
        print(f"Applied Migrations:   {len(applied)} / {len(MIGRATION_REVISIONS)}")
        for rev in MIGRATION_REVISIONS:
            mark = "X" if rev["revision"] in applied else " "
            print(f"  [{mark}] {rev['revision']:<30} ({rev['description']})")

        print("\nTable Schema Inventory:")
        for t in sorted(tables):
            cols = len(inspector.get_columns(t))
            pk = inspector.get_pk_constraint(t)
            print(f"  - {t:<22} ({cols} columns, PK: {pk.get('constrained_columns')})")
        print("================================\n")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if action == "status":
        status()
    elif action == "current":
        current()
    elif action == "history":
        history()
    elif action == "downgrade":
        downgrade()
    else:
        upgrade()
        status()
