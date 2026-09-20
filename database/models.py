from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(25), nullable=True)
    risk_profile = db.Column(db.String(30), nullable=False, default="Moderate")
    investment_goal = db.Column(db.String(120), nullable=True)
    preferred_market = db.Column(db.String(30), nullable=False, default="NSE")
    google_id = db.Column(db.String(255), unique=True, nullable=True, index=True)
    auth_provider = db.Column(db.String(30), nullable=False, default="email")

    # Relationships
    watchlist = db.relationship(
        "Watchlist",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )
    portfolios = db.relationship(
        "Portfolio",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )
    alerts = db.relationship(
        "StockAlert",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )


class Watchlist(db.Model):
    __tablename__ = "watchlist"
    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "symbol",
            name="unique_watchlist_stock"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    symbol = db.Column(
        db.String(20),
        nullable=False,
        index=True
    )
    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )


class Portfolio(db.Model):
    __tablename__ = "portfolios"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    name = db.Column(db.String(100), nullable=False, default="Primary Portfolio")
    currency = db.Column(db.String(10), nullable=False, default="INR")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    holdings = db.relationship(
        "Holding",
        backref="portfolio",
        lazy=True,
        cascade="all, delete-orphan"
    )
    transactions = db.relationship(
        "Transaction",
        backref="portfolio",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="desc(Transaction.created_at)"
    )
    snapshots = db.relationship(
        "PortfolioSnapshot",
        backref="portfolio",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="PortfolioSnapshot.snapshot_date"
    )


class Holding(db.Model):
    __tablename__ = "holdings"
    __table_args__ = (
        db.UniqueConstraint(
            "portfolio_id",
            "symbol",
            name="unique_portfolio_holding"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(
        db.Integer,
        db.ForeignKey("portfolios.id"),
        nullable=False,
        index=True
    )
    symbol = db.Column(db.String(20), nullable=False, index=True)
    stock_name = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=0.0)
    average_buy_price = db.Column(db.Float, nullable=False, default=0.0)
    sector = db.Column(db.String(60), nullable=True, default="Others")
    last_updated = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(
        db.Integer,
        db.ForeignKey("portfolios.id"),
        nullable=False,
        index=True
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    symbol = db.Column(db.String(20), nullable=False, index=True)
    stock_name = db.Column(db.String(150), nullable=False)
    transaction_type = db.Column(db.String(10), nullable=False)  # BUY or SELL
    quantity = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    fees = db.Column(db.Float, nullable=False, default=0.0)
    realized_pnl = db.Column(db.Float, nullable=True, default=0.0)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class PortfolioSnapshot(db.Model):
    __tablename__ = "portfolio_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(
        db.Integer,
        db.ForeignKey("portfolios.id"),
        nullable=False,
        index=True
    )
    total_value = db.Column(db.Float, nullable=False, default=0.0)
    total_invested = db.Column(db.Float, nullable=False, default=0.0)
    total_pnl = db.Column(db.Float, nullable=False, default=0.0)
    snapshot_date = db.Column(db.Date, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class StockAlert(db.Model):
    __tablename__ = "stock_alerts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    symbol = db.Column(db.String(20), nullable=False, index=True)
    alert_type = db.Column(db.String(30), nullable=False)  # PRICE_ABOVE, PRICE_BELOW, RSI_OVERSOLD, RSI_OVERBOUGHT, SIGNAL_CHANGE
    target_value = db.Column(db.Float, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    is_triggered = db.Column(db.Boolean, default=False, nullable=False)
    triggered_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class AIAnalysisCache(db.Model):
    __tablename__ = "ai_analysis_cache"

    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), unique=True, nullable=False, index=True)
    overall_score = db.Column(db.Integer, nullable=False)
    fundamental_score = db.Column(db.Integer, nullable=False)
    technical_score = db.Column(db.Integer, nullable=False)
    valuation_score = db.Column(db.Integer, nullable=False)
    momentum_score = db.Column(db.Integer, nullable=False)
    sentiment_score = db.Column(db.Integer, nullable=False)
    risk_score = db.Column(db.Integer, nullable=False)
    signal = db.Column(db.String(20), nullable=False)
    confidence = db.Column(db.Integer, nullable=False)
    target_price = db.Column(db.Float, nullable=True)
    stop_loss = db.Column(db.Float, nullable=True)
    summary_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=True, index=True)
