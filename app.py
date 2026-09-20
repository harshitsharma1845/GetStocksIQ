from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import yfinance as yf
import math
import os
import re

# from datetime import datetime
from datetime import datetime, timedelta, timezone

# from datetime import datetime
from datetime import datetime, timedelta, timezone
import feedparser
import random
import secrets
import smtplib
import ssl
from email.message import EmailMessage
from database.models import (
    db,
    User,
    Watchlist,
    Portfolio,
    Holding,
    Transaction,
    PortfolioSnapshot,
    StockAlert,
    AIAnalysisCache,
)
from sqlalchemy.exc import IntegrityError


from flask_bcrypt import Bcrypt

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)

from config import Config

from services.stock_service import StockService
from services.portfolio_service import PortfolioService
from services.llm_service import LLMService
from services.cache_service import CacheService
from services.news_service import NewsService
from services.scoring_service import ScoringEngine

import requests

try:
    from google.auth.transport import requests as google_auth_requests
    from google.oauth2 import id_token as google_id_token
except ImportError:
    google_auth_requests = None
    google_id_token = None

YFINANCE_CACHE_DIR = os.path.join(
    os.path.dirname(__file__),
    "instance",
    "yfinance_cache",
)

os.makedirs(YFINANCE_CACHE_DIR, exist_ok=True)

try:
    yf.set_tz_cache_location(YFINANCE_CACHE_DIR)
except AttributeError:
    pass

app = Flask(__name__)

app.config.from_object(Config)

# ==================================================
# CENTRALIZED INPUT VALIDATION HELPERS
# ==================================================

STOCK_SYMBOL_REGEX = re.compile(r"^[A-Za-z0-9._^+-]{1,20}$")


def validate_stock_symbol(symbol: str) -> str:
    """Validate and normalize stock symbols against strict allowlist."""
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Stock symbol must be a non-empty string.")
    cleaned = symbol.strip().upper()
    if not STOCK_SYMBOL_REGEX.match(cleaned):
        raise ValueError(f"Invalid stock symbol format: '{symbol}'.")
    return cleaned


def validate_trade_inputs(quantity_val, price_val, fees_val=0.0):
    """Validate numeric quantity, price, and fees with strict bounds checking."""
    try:
        q = float(quantity_val)
        if q != q or q == float("inf") or q == float("-inf"):
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError("Quantity must be a valid positive number.")
    if q < 1 or q > 1_000_000:
        raise ValueError("Quantity must be between 1 and 1,000,000.")

    try:
        p = float(price_val)
        if p != p or p == float("inf") or p == float("-inf"):
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError("Price must be a valid positive number.")
    if p < 0.01 or p > 10_000_000.0:
        raise ValueError("Price must be between ₹0.01 and ₹10,000,000.")

    try:
        f = float(fees_val or 0.0)
        if f != f or f == float("inf") or f == float("-inf"):
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError("Fees must be a valid non-negative number.")
    if f < 0.0 or f > 100_000.0:
        raise ValueError("Fees must be between ₹0 and ₹100,000.")

    return q, p, f


# ==================================================
# CSRF PROTECTION (SESSION TOKEN + DOUBLE-SUBMIT)
# ==================================================

def get_csrf_token() -> str:
    """Retrieve or generate a cryptographically secure CSRF token for the session."""
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


@app.context_processor
def inject_csrf_token():
    """Expose csrf_token() helper across all Jinja2 templates."""
    return {"csrf_token": get_csrf_token}


@app.before_request
def validate_csrf():
    """Validate CSRF tokens on all state-changing HTTP requests."""
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        # Testing bypass only if WTF_CSRF_ENABLED is explicitly False in test harness
        if app.config.get("TESTING") and app.config.get("WTF_CSRF_ENABLED") is False:
            return None

        # Google GIS OAuth route has its own ID token and custom CSRF token verification
        if request.path == "/auth/google":
            return None

        expected = session.get("csrf_token")
        if not expected:
            expected = get_csrf_token()

        submitted = None
        if request.form and "csrf_token" in request.form:
            submitted = request.form.get("csrf_token")
        elif request.is_json and isinstance(request.get_json(silent=True), dict):
            submitted = request.get_json(silent=True).get("csrf_token")

        if not submitted:
            submitted = (
                request.headers.get("X-CSRF-Token")
                or request.headers.get("X-CSRFToken")
                or request.headers.get("X-Csrf-Token")
            )

        if not submitted or not secrets.compare_digest(str(submitted), str(expected)):
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({
                    "success": False,
                    "message": "CSRF token missing or invalid.",
                }), 403
            flash("Your session expired or the CSRF token was invalid. Please try again.", "danger")
            return redirect(request.referrer or url_for("landing")), 403


# ==================================================
# SECURITY HEADERS & CONTENT SECURITY POLICY (CSP)
# ==================================================

@app.after_request
def add_security_headers(response):
    """Add secure HTTP response headers to every request."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"

    csp_directives = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.plot.ly https://accounts.google.com",
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com",
        "font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.gstatic.com",
        "img-src 'self' data: https:",
        "connect-src 'self' https://accounts.google.com https://cdn.plot.ly",
        "frame-src 'self' https://accounts.google.com",
    ]
    response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

    # Enable HSTS only when operating in HTTPS production
    if request.is_secure or app.config.get("SESSION_COOKIE_SECURE"):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


# ==================================================
# GLOBAL SAFE ERROR HANDLERS
# ==================================================

@app.errorhandler(400)
def handle_bad_request(e):
    if request.is_json or request.path.startswith("/api/"):
        return jsonify({"success": False, "message": "Bad request: invalid parameters provided."}), 400
    return render_template("base.html", custom_error="400 Bad Request - Invalid parameters provided."), 400


@app.errorhandler(403)
def handle_forbidden(e):
    if request.is_json or request.path.startswith("/api/"):
        return jsonify({"success": False, "message": "Access forbidden: invalid credentials, CSRF failure, or unauthorized resource access."}), 403
    return render_template("base.html", custom_error="403 Forbidden - Access denied or invalid CSRF token."), 403


@app.errorhandler(404)
def handle_not_found(e):
    if request.is_json or request.path.startswith("/api/"):
        return jsonify({"success": False, "message": "Requested resource not found."}), 404
    return render_template("base.html", custom_error="404 Not Found - The requested resource could not be found."), 404


@app.errorhandler(405)
def handle_method_not_allowed(e):
    if request.is_json or request.path.startswith("/api/"):
        return jsonify({"success": False, "message": "HTTP method not allowed."}), 405
    return render_template("base.html", custom_error="405 Method Not Allowed."), 405


@app.errorhandler(413)
def handle_payload_too_large(e):
    if request.is_json or request.path.startswith("/api/"):
        return jsonify({"success": False, "message": "Payload too large: request body exceeds maximum allowed 16MB limit."}), 413
    return render_template("base.html", custom_error="413 Payload Too Large - Request body exceeds limit."), 413


@app.errorhandler(429)
def handle_too_many_requests(e):
    if request.is_json or request.path.startswith("/api/"):
        return jsonify({"success": False, "message": "Too many requests. Please slow down and try again later."}), 429
    return render_template("base.html", custom_error="429 Too Many Requests - Please try again later."), 429


@app.errorhandler(500)
def handle_server_error(e):
    app.logger.error(f"Internal server error: {e}")
    if request.is_json or request.path.startswith("/api/"):
        return jsonify({"success": False, "message": "An internal server error occurred. Please try again later."}), 500
    return render_template("base.html", custom_error="500 Internal Server Error - An unexpected error occurred."), 500



POPULAR_STOCKS = [
    {"symbol": "RELIANCE.NS", "display_symbol": "RELIANCE", "name": "Reliance Industries", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "TCS.NS", "display_symbol": "TCS", "name": "Tata Consultancy Services", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "INFY.NS", "display_symbol": "INFY", "name": "Infosys Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "HDFCBANK.NS", "display_symbol": "HDFCBANK", "name": "HDFC Bank", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "ICICIBANK.NS", "display_symbol": "ICICIBANK", "name": "ICICI Bank", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "SBIN.NS", "display_symbol": "SBIN", "name": "State Bank of India", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "BHARTIARTL.NS", "display_symbol": "BHARTIARTL", "name": "Bharti Airtel", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "ITC.NS", "display_symbol": "ITC", "name": "ITC Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "LT.NS", "display_symbol": "LT", "name": "Larsen & Toubro", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "AXISBANK.NS", "display_symbol": "AXISBANK", "name": "Axis Bank", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "MARUTI.NS", "display_symbol": "MARUTI", "name": "Maruti Suzuki", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "TATAMOTORS.NS", "display_symbol": "TATAMOTORS", "name": "Tata Motors", "exchange": "NSE", "type": "EQUITY"},
]

MARKET_WATCH_SYMBOLS = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "BHARTIARTL.NS",
    "ITC.NS",
    "LT.NS",
    "AXISBANK.NS",
    "MARUTI.NS",
    "WIPRO.NS",
    "HCLTECH.NS",
    "KOTAKBANK.NS",
    "BAJFINANCE.NS",
    "SUNPHARMA.NS",
    "ULTRACEMCO.NS",
    "ASIANPAINT.NS",
    "TITAN.NS",
    "POWERGRID.NS",
    "NTPC.NS",
    "ONGC.NS",
    "ADANIENT.NS",
]


def detect_stock_from_question(question):
    stripped_question = question.strip()
    normalized_question = question.upper()

    index_aliases = {
        "NIFTY 50": "^NSEI",
        "NIFTY": "^NSEI",
        "SENSEX": "^BSESN",
        "BSE": "^BSESN",
    }

    for alias, symbol in index_aliases.items():
        if alias in normalized_question:
            return symbol

    for stock in POPULAR_STOCKS:
        aliases = [
            stock["symbol"].upper(),
            stock["display_symbol"].upper(),
            stock["name"].upper(),
        ]

        if any(alias in normalized_question for alias in aliases):
            return stock["symbol"]

    words = [
        word.strip(".,?!()[]{}:;\"'")
        for word in stripped_question.split()
    ]

    for word in words:
        clean_word = word.upper()

        if clean_word.endswith((".NS", ".BO")):
            return clean_word

        if 2 <= len(clean_word) <= 12 and clean_word.isalpha() and word.isupper():
            return f"{clean_word}.NS"

    return ""


def get_ai_stock_context(symbol):
    if not symbol:
        return "No specific stock symbol was detected in the question."

    try:
        stock = StockService.get_stock_details(symbol)

        if not stock:
            return f"Stock symbol detected: {symbol}. Live details are unavailable."

        return (
            f"Detected stock: {stock.get('name', symbol)} ({stock.get('symbol', symbol)}). "
            f"Current price: {stock.get('price', 'N/A')}. "
            f"Change: {stock.get('price_change', 'N/A')}. "
            f"Volume: {stock.get('volume', 'N/A')}. "
            f"Day range: {stock.get('day_low', 'N/A')} - {stock.get('day_high', 'N/A')}. "
            f"52-week range: {stock.get('low52', 'N/A')} - {stock.get('high52', 'N/A')}."
        )

    except Exception as error:
        print("Ask AI stock context error:", error)
        return f"Stock symbol detected: {symbol}. Live details are temporarily unavailable."


def parse_percent_value(value):
    try:
        if value is None:
            return 0.0

        cleaned_value = str(value).replace("%", "").replace("+", "").strip()
        return float(cleaned_value)

    except (TypeError, ValueError):
        return 0.0


def parse_price_value(value):
    try:
        if value is None:
            return 0.0

        cleaned_value = (
            str(value)
            .replace("₹", "")
            .replace(",", "")
            .replace("N/A", "")
            .strip()
        )

        return float(cleaned_value) if cleaned_value else 0.0

    except (TypeError, ValueError):
        return 0.0


def get_dashboard_stock_snapshot(symbol):
    raw_symbol = (symbol or "").strip().upper()

    symbol_aliases = {
        "BSE": "BSE.NS",
        "IDEA": "IDEA.NS",
        "NIFTY": "^NSEI",
        "NIFTY50": "^NSEI",
        "SENSEX": "^BSESN",
    }

    normalized_symbol = symbol_aliases.get(raw_symbol, raw_symbol)

    if normalized_symbol.startswith("^"):
        candidates = [normalized_symbol]
    elif "." in normalized_symbol:
        candidates = [normalized_symbol]
    else:
        candidates = [f"{normalized_symbol}.NS", f"{normalized_symbol}.BO", normalized_symbol]

    details = None
    selected_symbol = candidates[0] if candidates else raw_symbol

    for candidate in candidates:
        try:
            details = StockService.get_stock_details(candidate)

            if details and details.get("price") != "N/A":
                selected_symbol = details.get("symbol", candidate)
                break

        except Exception as error:
            print("Dashboard service snapshot error:", error)

    if not details or details.get("price") == "N/A":
        for candidate in candidates:
            try:
                ticker = yf.Ticker(candidate)
                info = {}
                fast_info = {}

                try:
                    info = ticker.info or {}
                except Exception:
                    info = {}

                try:
                    fast_info = ticker.fast_info or {}
                except Exception:
                    fast_info = {}

                history = ticker.history(period="5d", interval="1d", auto_adjust=False)

                close_prices = (
                    history["Close"].dropna()
                    if not history.empty and "Close" in history.columns
                    else []
                )

                current_price = (
                    fast_info.get("lastPrice")
                    or info.get("currentPrice")
                    or info.get("regularMarketPrice")
                    or (float(close_prices.iloc[-1]) if len(close_prices) else None)
                )

                previous_price = (
                    fast_info.get("previousClose")
                    or info.get("previousClose")
                    or info.get("regularMarketPreviousClose")
                    or (
                        float(close_prices.iloc[-2])
                        if len(close_prices) >= 2
                        else None
                    )
                )

                if current_price is None:
                    continue

                selected_symbol = candidate
                price = f"{float(current_price):,.2f}"
                change_value = 0.0

                if previous_price:
                    try:
                        c_val = float(current_price)
                        p_val = float(previous_price)
                        if p_val > 0 and not math.isnan(c_val) and not math.isnan(p_val):
                            calc = ((c_val - p_val) / p_val) * 100
                            if not math.isnan(calc) and not math.isinf(calc):
                                change_value = round(calc, 2)
                    except Exception:
                        change_value = 0.0

                display_symbol = candidate.replace(".NS", "").replace(".BO", "")
                change_percent = f"{change_value:+.2f}%"

                details = {
                    "symbol": candidate,
                    "name": info.get("longName") or info.get("shortName") or display_symbol,
                    "price": price,
                    "price_change": change_percent,
                    "price_change_value": change_value,
                }

                break

            except Exception as error:
                print("Dashboard yfinance snapshot error:", error)

    display_symbol = selected_symbol.replace(".NS", "").replace(".BO", "")

    if not details:
        return {
            "symbol": display_symbol,
            "name": display_symbol,
            "price": "N/A",
            "change_percent": "N/A",
            "change_value": 0.0,
            "signal": "HOLD",
            "is_live": False,
        }

    change_percent = details.get("price_change", "+0.00%")
    change_value = details.get("price_change_value")

    if change_value is None:
        change_value = parse_percent_value(change_percent)

    if change_value >= 1.5:
        signal = "BUY"
    elif change_value <= -1.5:
        signal = "WAIT"
    else:
        signal = "HOLD"

    return {
        "symbol": display_symbol,
        "name": details.get("name", display_symbol),
        "price": details.get("price", "N/A"),
        "change_percent": change_percent,
        "change_value": change_value,
        "signal": signal,
        "is_live": details.get("price", "N/A") != "N/A",
    }


def get_dashboard_batch_snapshots(symbols):
    if not symbols:
        return []

    cache_key = "dashboard_market_movers"

    def _fetch():
        unique_symbols = list(dict.fromkeys(symbols))

        name_lookup = {
            stock["symbol"]: stock["name"]
            for stock in POPULAR_STOCKS
        }

        snapshots = []

        try:
            data = yf.download(
                tickers=unique_symbols,
                period="5d",
                interval="1d",
                group_by="ticker",
                auto_adjust=False,
                progress=False,
                threads=True,
            )

            for symbol in unique_symbols:
                try:
                    if len(unique_symbols) == 1:
                        history = data
                    else:
                        history = data[symbol]

                    close_prices = history["Close"].dropna()

                    if close_prices.empty:
                        continue

                    current_price = float(close_prices.iloc[-1])
                    previous_price = (
                        float(close_prices.iloc[-2])
                        if len(close_prices) >= 2
                        else current_price
                    )

                    change_value = 0.0

                    if previous_price and not math.isnan(current_price) and not math.isnan(previous_price) and previous_price > 0:
                        calc = ((current_price - previous_price) / previous_price) * 100
                        if not math.isnan(calc) and not math.isinf(calc):
                            change_value = round(calc, 2)

                    if change_value >= 1.5:
                        signal = "BUY"
                    elif change_value <= -1.5:
                        signal = "WAIT"
                    else:
                        signal = "HOLD"

                    display_symbol = symbol.replace(".NS", "").replace(".BO", "")

                    item = {
                        "symbol": display_symbol,
                        "raw_symbol": symbol,
                        "name": name_lookup.get(symbol, display_symbol),
                        "price": f"{current_price:,.2f}",
                        "raw_price": current_price,
                        "change_percent": f"{change_value:+.2f}%",
                        "change_value": change_value,
                        "signal": signal,
                        "is_live": True,
                    }
                    snapshots.append(item)

                    # Populate fast price cache for in-request and portfolio sharing
                    CacheService.set(
                        f"price_{symbol}",
                        (current_price, change_value, (current_price - previous_price)),
                        ttl_seconds=CacheService.TTL_MARKET_MOVERS
                    )

                except Exception as error:
                    print(f"Dashboard batch symbol error for {symbol}:", error)

        except Exception as error:
            print("Dashboard batch snapshot error:", error)

        return snapshots

    try:
        return CacheService.get_or_set(
            cache_key,
            _fetch,
            ttl_seconds=CacheService.TTL_MARKET_MOVERS,
            allow_stale=True
        ) or []
    except Exception as e:
        print("Dashboard batch movers error:", e)
        stale = CacheService.get(cache_key, allow_stale=True)
        return stale if stale is not None else []


# ==================================================
# DATABASE
# ==================================================

db.init_app(app)


# ==================================================
# PASSWORD ENCRYPTION
# ==================================================

bcrypt = Bcrypt(app)


# ==================================================
# LOGIN MANAGER
# ==================================================

login_manager = LoginManager(app)

login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):

    return db.session.get(User, int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for("login"))


# ==================================================
# CREATE DATABASE TABLES & SCHEMA SYNCHRONIZATION
# ==================================================

with app.app_context():
    db.create_all()

    try:
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        if "users" in inspector.get_table_names():
            existing_cols = {col["name"] for col in inspector.get_columns("users")}

            def ensure_column_cross_dialect(column_name, column_definition):
                if column_name not in existing_cols:
                    db.session.execute(
                        db.text(
                            f"ALTER TABLE users "
                            f"ADD COLUMN {column_name} {column_definition}"
                        )
                    )
                    db.session.commit()
                    existing_cols.add(column_name)

            ensure_column_cross_dialect("phone", "VARCHAR(25)")
            ensure_column_cross_dialect("risk_profile", "VARCHAR(30) DEFAULT 'Moderate' NOT NULL")
            ensure_column_cross_dialect("investment_goal", "VARCHAR(120)")
            ensure_column_cross_dialect("preferred_market", "VARCHAR(30) DEFAULT 'NSE' NOT NULL")
            ensure_column_cross_dialect("google_id", "VARCHAR(255)")
            ensure_column_cross_dialect("auth_provider", "VARCHAR(30) DEFAULT 'email' NOT NULL")

            db.session.execute(
                db.text("UPDATE users SET auth_provider = 'email' WHERE auth_provider IS NULL OR auth_provider = ''")
            )
            db.session.commit()
    except Exception as e:
        app.logger.warning(f"Schema inspection / migration sync notice: {e}")
        db.session.rollback()


def send_otp_email(recipient, otp):
    mail_server = app.config.get("MAIL_SERVER")
    mail_username = app.config.get("MAIL_USERNAME")
    mail_password = app.config.get("MAIL_PASSWORD")
    mail_sender = app.config.get("MAIL_DEFAULT_SENDER") or mail_username
    mail_port = int(app.config.get("MAIL_PORT") or 587)

    if not mail_server or not mail_username or not mail_password or not mail_sender:
        print(f"Password reset OTP for {recipient}: {otp}")
        return False

    message = EmailMessage()
    message["Subject"] = "Your GetStockIQ OTP"
    message.set_content(
        "Use this OTP to reset your password:\n\n"
        f"{otp}\n\n"
        "This OTP will expire in 10 minutes."
    )

    context = ssl.create_default_context()

    with smtplib.SMTP(mail_server, mail_port) as server:
        server.starttls(context=context)
        server.login(mail_username, mail_password)
        server.send_message(message)

    return True


# ==================================================
# LOGIN
# ==================================================


@app.route("/")
def landing():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_login_form()

        user = db.session.execute(
            db.select(User).filter_by(email=email)
        ).scalar_one_or_none()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)

            return redirect(url_for("dashboard"))

        flash("Invalid Email or Password", "danger")

    return render_login_form()


def render_login_form():
    """Render the normal login form plus the public GIS client configuration."""
    google_csrf_token = session.get("google_login_csrf")
    if not google_csrf_token:
        google_csrf_token = secrets.token_urlsafe(32)
        session["google_login_csrf"] = google_csrf_token

    return render_template(
        "login_form.html",
        google_client_id=app.config.get("GOOGLE_CLIENT_ID"),
        google_csrf_token=google_csrf_token,
    )


@app.route("/auth/google", methods=["POST"])
def google_login():
    """Verify a Google ID token and link or create the matching InvestIQ account."""
    if current_user.is_authenticated:
        return jsonify({"success": True, "redirect": url_for("dashboard")})

    client_id = app.config.get("GOOGLE_CLIENT_ID")
    if not client_id or not google_id_token or not google_auth_requests:
        return jsonify({"success": False, "message": "Google sign-in is not configured yet."}), 503

    payload = request.get_json(silent=True) or {}
    csrf_token = str(payload.get("csrf_token", ""))
    expected_csrf_token = str(session.get("google_login_csrf", ""))
    if not expected_csrf_token or not secrets.compare_digest(csrf_token, expected_csrf_token):
        return jsonify({"success": False, "message": "Your sign-in session expired. Refresh the page and try again."}), 403

    credential = payload.get("credential", "")
    if not credential:
        return jsonify({"success": False, "message": "Google did not return a sign-in credential. Please try again."}), 400

    try:
        token_data = google_id_token.verify_oauth2_token(
            credential,
            google_auth_requests.Request(),
            client_id,
        )
    except ValueError:
        return jsonify({"success": False, "message": "Google sign-in could not be verified. Please try again."}), 401
    except Exception:
        app.logger.exception("Google token verification failed")
        return jsonify({"success": False, "message": "Unable to verify Google sign-in right now. Please try again."}), 503

    email = str(token_data.get("email", "")).strip().lower()
    google_id = str(token_data.get("sub", "")).strip()
    full_name = str(token_data.get("name") or email.split("@")[0]).strip()

    if token_data.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        return jsonify({"success": False, "message": "Google sign-in could not be verified. Please try again."}), 401

    if not email or not google_id or token_data.get("email_verified") is not True:
        return jsonify({"success": False, "message": "Use a verified Google email address to sign in."}), 401

    try:
        google_user = db.session.execute(db.select(User).filter_by(google_id=google_id)).scalar_one_or_none()
        email_user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()
        if google_user and email_user and google_user.id != email_user.id:
            return jsonify({"success": False, "message": "This Google account is already linked to another user."}), 409

        user = google_user or email_user
        if user:
            if user.google_id and user.google_id != google_id:
                return jsonify({"success": False, "message": "This email is already linked to another Google account."}), 409
            user.google_id = google_id
            if user.auth_provider == "email":
                user.auth_provider = "email_google"
        else:
            generated_password = bcrypt.generate_password_hash(secrets.token_urlsafe(32)).decode("utf-8")
            user = User(
                full_name=full_name[:100],
                email=email,
                password=generated_password,
                google_id=google_id,
                auth_provider="google",
            )
            db.session.add(user)

        db.session.commit()
        login_user(user)
        session.pop("google_login_csrf", None)
        return jsonify({"success": True, "redirect": url_for("dashboard")})
    except IntegrityError:
        db.session.rollback()
        return jsonify({"success": False, "message": "This Google account is already linked to another user."}), 409
    except Exception:
        db.session.rollback()
        app.logger.exception("Google account sign-in failed")
        return jsonify({"success": False, "message": "Unable to sign in with Google right now. Please try again."}), 500


# ==================================================
# REGISTER
# ==================================================


@app.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        fullname = request.form.get("fullname", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not fullname or not email or not password or not confirm:
            flash("All registration fields are required.", "danger")
            return redirect(url_for("register"))

        # ------------------------------
        # CHECK PASSWORDS
        # ------------------------------

        if password != confirm:
            flash("Passwords do not match", "danger")

            return redirect(url_for("register"))

        # ------------------------------
        # CHECK EXISTING EMAIL
        # ------------------------------

        existing = db.session.execute(
            db.select(User).filter_by(email=email)
        ).scalar_one_or_none()

        if existing:
            flash("Email already exists", "danger")

            return redirect(url_for("register"))

        # ------------------------------

        # ------------------------------
        # CHECK PASSWORDS
        # ------------------------------
        # HASH PASSWORD
        # ------------------------------

        hashed = bcrypt.generate_password_hash(password).decode("utf-8")

        # ------------------------------
        # CREATE USER
        # ------------------------------

        new_user = User(full_name=fullname, email=email, password=hashed)

        db.session.add(new_user)
        db.session.commit()

        flash("Registration Successful", "success")

        return redirect(url_for("login"))

    return render_template("register.html")


# ==================================================
# DASHBOARD
# ==================================================

@app.route("/dashboard")
@login_required
def dashboard():
    # Get current NIFTY and SENSEX values
    market = StockService.get_market_data()
    market_chart = None

    # 1. Real Authenticated User Portfolio Summary
    user_portfolio = PortfolioService.get_or_create_portfolio(current_user.id)
    portfolio_summary = PortfolioService.get_portfolio_summary(user_portfolio.id)

    if portfolio_summary["has_holdings"]:
        dashboard_data = {
            "portfolio_value": f"₹{portfolio_summary['total_value']:,.2f}",
            "today_change": f"{portfolio_summary['today_pnl_pct']:+.2f}%",
            "total_return": f"{portfolio_summary['total_return_pct']:+.2f}%",
            "total_pnl": f"₹{portfolio_summary['total_pnl']:,.2f}",
            "holdings_count": portfolio_summary["holdings_count"],
            "health_score": portfolio_summary["health_score"],
            "health_label": portfolio_summary["health_label"],
            "nifty": market["nifty"],
            "nifty_change": market["status"],
            "sensex": market["sensex"],
            "sensex_change": market["status"],
        }
        holdings = portfolio_summary["holdings"][:5]
        allocation = portfolio_summary["sector_allocation"]
    else:
        dashboard_data = {
            "portfolio_value": "₹0.00",
            "today_change": "0.00%",
            "total_return": "0.00%",
            "total_pnl": "₹0.00",
            "holdings_count": 0,
            "health_score": None,
            "health_label": "No Holdings",
            "nifty": market["nifty"],
            "nifty_change": market["status"],
            "sensex": market["sensex"],
            "sensex_change": market["status"],
        }
        holdings = []
        allocation = []

    # 2. Live Market Movers (Gainers / Losers)
    live_movers = get_dashboard_batch_snapshots(MARKET_WATCH_SYMBOLS)
    top_gainers = sorted(
        [stock for stock in live_movers if stock.get("change_value", 0) > 0],
        key=lambda stock: stock.get("change_value", 0),
        reverse=True,
    )[:3]

    top_losers = sorted(
        [stock for stock in live_movers if stock.get("change_value", 0) < 0],
        key=lambda stock: stock.get("change_value", 0),
    )[:3]

    # 3. Deterministic Scored Recommendations from Active Universe
    def _fetch_recommendations():
        recommended_candidates = [
            "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS",
            "ICICIBANK.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS"
        ]
        # Fast batch snapshot instead of 8 sequential individual network requests
        snaps = get_dashboard_batch_snapshots(recommended_candidates)
        pool = []
        for snap in snaps:
            sym = snap.get("raw_symbol") or f"{snap.get('symbol')}.NS"
            cached_ai = CacheService.get(f"ai_analysis_{sym}", allow_stale=True)
            if cached_ai:
                snap["signal"] = cached_ai.get("signal", "HOLD")
                snap["overall_score"] = cached_ai.get("overall", 50)
            else:
                change = snap.get("change_value", 0.0)
                if change >= 1.5:
                    snap["signal"] = "STRONG BUY"
                    snap["overall_score"] = 85
                elif change >= 0.3:
                    snap["signal"] = "BUY"
                    snap["overall_score"] = 72
                elif change <= -1.5:
                    snap["signal"] = "REDUCE"
                    snap["overall_score"] = 45
                else:
                    snap["signal"] = "HOLD"
                    snap["overall_score"] = 60
            pool.append(snap)

        pool.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
        return pool[:4]

    try:
        recommended_stocks = CacheService.get_or_set(
            "dashboard_recommended_stocks",
            _fetch_recommendations,
            ttl_seconds=CacheService.TTL_RECOMMENDATIONS,
            allow_stale=True
        ) or []
    except Exception as e:
        print("Dashboard recommendations error:", e)
        stale_rec = CacheService.get("dashboard_recommended_stocks", allow_stale=True)
        recommended_stocks = stale_rec if stale_rec is not None else []

    # 4. Live Market News
    market_news = NewsService.get_market_news()

    return render_template(
        "dashboard.html",
        data=dashboard_data,
        market_chart=market_chart,
        market_news=market_news,
        holdings=holdings,
        portfolio_summary=portfolio_summary,
        allocation=allocation,
        recommended_stocks=recommended_stocks,
        top_gainers=top_gainers,
        top_losers=top_losers,
    )


@app.route("/api/search-stocks")
@login_required
def stock_search():

    query = request.args.get("q", "").strip()

    # Do not call Yahoo for empty input

    if len(query) < 1:
        return jsonify([])

    def fallback_suggestions():
        lowered_query = query.lower()

        return [
            stock
            for stock in POPULAR_STOCKS
            if lowered_query in stock["symbol"].lower()
            or lowered_query in stock["display_symbol"].lower()
            or lowered_query in stock["name"].lower()
        ][:8]

    try:
        yahoo_url = "https://query2.finance.yahoo.com/v1/finance/search"

        parameters = {
            "q": query,
            "quotesCount": 15,
            "newsCount": 0,
            "enableFuzzyQuery": "true",
            "quotesQueryId": "tss_match_phrase_query",
        }

        headers = {"User-Agent": "Mozilla/5.0"}

        response = requests.get(
            yahoo_url, params=parameters, headers=headers, timeout=6
        )

        response.raise_for_status()

        yahoo_data = response.json()

        yahoo_quotes = yahoo_data.get("quotes", [])

        suggestions = []

        # ------------------------------------------
        # CREATE CLEAN STOCK SUGGESTIONS
        # ------------------------------------------

        for stock in yahoo_quotes:
            quote_type = stock.get("quoteType", "").upper()

            # Only show stocks and ETFs

            if quote_type not in ["EQUITY", "ETF"]:
                continue

            symbol = stock.get("symbol", "").strip()

            if not symbol:
                continue

            company_name = stock.get("longname") or stock.get("shortname") or symbol

            exchange = stock.get("exchDisp") or stock.get("exchange", "")

            # Symbol shown in UI:
            # TCS.NS -> TCS
            # IDEA.NS -> IDEA

            display_symbol = symbol.replace(".NS", "").replace(".BO", "")

            suggestions.append(
                {
                    # Exact Yahoo symbol sent
                    # to analysis page
                    "symbol": symbol,
                    # Clean symbol shown
                    # inside dropdown
                    "display_symbol": display_symbol,
                    "name": company_name,
                    "exchange": exchange,
                    "type": quote_type,
                }
            )

        # ------------------------------------------
        # SHOW INDIAN NSE RESULTS FIRST
        # ------------------------------------------

        suggestions.sort(key=lambda item: 0 if item["symbol"].endswith(".NS") else 1)

        return jsonify(suggestions[:8] or fallback_suggestions())

    except Exception as error:
        print("Stock Search Error:", error)

        return jsonify(fallback_suggestions())


# ==================================================
# PORTFOLIO MANAGEMENT
# ==================================================

@app.route("/portfolio")
@login_required
def portfolio():
    user_portfolio = PortfolioService.get_or_create_portfolio(current_user.id)
    summary = PortfolioService.get_portfolio_summary(user_portfolio.id)
    transactions = (
        Transaction.query.filter_by(portfolio_id=user_portfolio.id)
        .order_by(Transaction.created_at.desc())
        .limit(50)
        .all()
    )
    return render_template(
        "portfolio.html",
        portfolio=user_portfolio,
        summary=summary,
        transactions=transactions,
    )


@app.route("/api/health/db", methods=["GET"])
def api_db_health():
    """Lightweight database connectivity check executing trivial SELECT 1."""
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "dialect": db.engine.dialect.name,
        }), 200
    except Exception as error:
        app.logger.error(f"Database health check failure: {error}")
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "message": "Database connectivity check failed.",
        }), 503


@app.route("/api/portfolio/summary")
@login_required
def api_portfolio_summary():
    user_portfolio = PortfolioService.get_or_create_portfolio(current_user.id)
    summary = PortfolioService.get_portfolio_summary(user_portfolio.id)
    return jsonify({"success": True, "data": summary})


@app.route("/api/portfolio/buy", methods=["POST"])
@login_required
def api_portfolio_buy():
    data = request.get_json(silent=True) or request.form
    try:
        raw_symbol = data.get("symbol")
        symbol = validate_stock_symbol(raw_symbol)
        qty, price, fees = validate_trade_inputs(
            data.get("quantity"),
            data.get("price"),
            data.get("fees", 0.0),
        )
        notes = (data.get("notes") or "").strip()[:500]

        user_portfolio = PortfolioService.get_or_create_portfolio(current_user.id)
        holding, txn = PortfolioService.record_buy(
            portfolio_id=user_portfolio.id,
            user_id=current_user.id,
            symbol=symbol,
            quantity=qty,
            price=price,
            fees=fees,
            notes=notes,
        )

        return jsonify({
            "success": True,
            "message": f"Successfully purchased {qty:g} shares of {holding.symbol} at ₹{price:,.2f}.",
            "holding": {
                "id": holding.id,
                "symbol": holding.symbol,
                "quantity": holding.quantity,
                "avg_price": holding.average_buy_price,
            },
        })
    except ValueError as ve:
        return jsonify({"success": False, "message": str(ve)}), 400
    except Exception as error:
        app.logger.error(f"Portfolio buy error: {error}")
        return jsonify({"success": False, "message": str(error)}), 400


@app.route("/api/portfolio/sell", methods=["POST"])
@login_required
def api_portfolio_sell():
    data = request.get_json(silent=True) or request.form
    try:
        raw_symbol = data.get("symbol")
        symbol = validate_stock_symbol(raw_symbol)
        qty, price, fees = validate_trade_inputs(
            data.get("quantity"),
            data.get("price"),
            data.get("fees", 0.0),
        )
        notes = (data.get("notes") or "").strip()[:500]

        user_portfolio = PortfolioService.get_or_create_portfolio(current_user.id)
        holding, txn = PortfolioService.record_sell(
            portfolio_id=user_portfolio.id,
            user_id=current_user.id,
            symbol=symbol,
            quantity=qty,
            price=price,
            fees=fees,
            notes=notes,
        )

        pnl_str = f"+₹{txn.realized_pnl:,.2f}" if txn.realized_pnl >= 0 else f"-₹{abs(txn.realized_pnl):,.2f}"
        return jsonify({
            "success": True,
            "message": f"Successfully sold {qty:g} shares of {symbol} at ₹{price:,.2f}. Realized P&L: {pnl_str}",
            "realized_pnl": txn.realized_pnl,
            "remaining_qty": holding.quantity if holding else 0.0,
        })
    except ValueError as ve:
        return jsonify({"success": False, "message": str(ve)}), 400
    except Exception as error:
        app.logger.error(f"Portfolio sell error: {error}")
        return jsonify({"success": False, "message": str(error)}), 400


@app.route("/api/portfolio/analyze-ai", methods=["POST"])
@app.route("/api/portfolio/ai-analysis", methods=["POST"])
@login_required
def api_portfolio_analyze_ai():
    user_portfolio = PortfolioService.get_or_create_portfolio(current_user.id)
    summary = PortfolioService.get_portfolio_summary(user_portfolio.id)
    analysis = LLMService.analyze_portfolio_ai(summary)
    return jsonify(analysis)


@app.route("/api/portfolio/transactions")
@login_required
def api_portfolio_transactions():
    user_portfolio = PortfolioService.get_or_create_portfolio(current_user.id)
    txns = (
        Transaction.query.filter_by(portfolio_id=user_portfolio.id)
        .order_by(Transaction.created_at.desc())
        .limit(100)
        .all()
    )
    result = [
        {
            "id": t.id,
            "symbol": t.symbol,
            "display_symbol": t.symbol.replace(".NS", "").replace(".BO", ""),
            "stock_name": t.stock_name,
            "type": t.transaction_type,
            "quantity": t.quantity,
            "price": t.price,
            "total_amount": t.total_amount,
            "fees": t.fees,
            "realized_pnl": t.realized_pnl,
            "notes": t.notes,
            "date": t.created_at.strftime("%d %b %Y, %I:%M %p") if t.created_at else "",
        }
        for t in txns
    ]
    return jsonify({"success": True, "transactions": result})


@app.route("/api/portfolio/holding/<int:holding_id>", methods=["DELETE", "POST"])
@login_required
def api_portfolio_delete_holding(holding_id):
    user_portfolio = PortfolioService.get_or_create_portfolio(current_user.id)
    holding = Holding.query.filter_by(id=holding_id, portfolio_id=user_portfolio.id).first()
    if not holding:
        return jsonify({"success": False, "message": "Holding not found."}), 404

    db.session.delete(holding)
    db.session.commit()
    return jsonify({"success": True, "message": "Holding removed successfully."})


# ==================================================
# ASK AI STOCK ASSISTANT
# ==================================================

@app.route("/api/ask-ai", methods=["POST"])
@login_required
def ask_ai():
    payload = request.get_json(silent=True) or {}
    raw_question = payload.get("question") or payload.get("message")
    if not raw_question or not isinstance(raw_question, str) or not raw_question.strip():
        return jsonify({
            "success": False,
            "message": "Please enter a stock or portfolio question.",
        }), 400

    question = raw_question.strip()
    if len(question) > 1000:
        return jsonify({
            "success": False,
            "message": "Question is too long (maximum 1,000 characters allowed).",
        }), 400

    detected_symbol = detect_stock_from_question(question)
    stock_context = get_ai_stock_context(detected_symbol) if detected_symbol else None

    result = LLMService.ask_financial_assistant(
        question=question,
        user_id=current_user.id,
        current_stock_context=stock_context,
    )
    result["symbol"] = detected_symbol
    status_code = 200 if result.get("success") else 503
    return jsonify(result), status_code


# ==================================================
# STOCK ANALYSIS
# ==================================================


@app.route("/analysis")
@login_required
def analysis():

    symbol = request.args.get("symbol", "").strip()



    if not symbol:
        return render_template(
            "analysis.html", stock=None, chart=None, news=[], ai=None
        )

    # Get company information
    stock = StockService.get_stock_details(symbol)

    # Get six-month stock chart
    chart = StockService.get_stock_chart(symbol)

    # Get latest company news
    news = StockService.get_stock_news(symbol)

    ai = StockService.get_ai_analysis(symbol)

    return render_template("analysis.html", stock=stock, chart=chart, news=news, ai=ai)


# ==================================================
# LOGOUT
# ==================================================


@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(url_for("landing"))


# ==================================================
# FORGOT PASSWORD
# ==================================================


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.args.get("restart"):
        session.pop("reset_email", None)
        session.pop("reset_otp", None)
        session.pop("reset_otp_expires", None)
        session.pop("reset_step", None)
        return redirect(url_for("forgot_password"))

    # If currently in verify or reset step, verify the OTP hasn't expired
    if session.get("reset_step") in ["verify", "reset"]:
        expires_raw = session.get("reset_otp_expires")
        try:
            expires_at = datetime.fromisoformat(expires_raw) if expires_raw else None
            if expires_at and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            expires_at = None

        if not expires_at or datetime.now(timezone.utc) > expires_at:
            session.pop("reset_email", None)
            session.pop("reset_otp", None)
            session.pop("reset_otp_expires", None)
            session.pop("reset_step", None)

    step = session.get("reset_step", "request")

    if request.method == "POST":
        action = request.form.get("action", "send_otp")

        if action == "send_otp":
            email = request.form.get("email", "").strip().lower()

            if not email:
                flash("Please enter your registered email address.", "danger")
                return redirect(url_for("forgot_password"))

            user = db.session.execute(
                db.select(User).filter_by(email=email)
            ).scalar_one_or_none()

            if not user:
                flash("❌ This email is not registered with us. Please check or sign up.", "danger")
                return redirect(url_for("forgot_password"))

            otp = f"{random.randint(100000, 999999)}"
            session["reset_email"] = email
            session["reset_otp"] = otp
            session["reset_otp_expires"] = (
                datetime.now(timezone.utc) + timedelta(minutes=10)
            ).isoformat()
            session["reset_step"] = "verify"

            try:
                email_sent = send_otp_email(email, otp)

                if email_sent:
                    flash(f"OTP sent to {email}.", "success")
                else:
                    flash(f"🔑 Dev Mode OTP: {otp}", "info")

            except Exception as error:
                print("OTP email error:", error)
                flash(f"🔑 Dev Mode OTP: {otp}", "info")

            return redirect(url_for("forgot_password"))

        if action == "verify_otp":
            entered_otp = request.form.get("otp", "").strip()
            expires_raw = session.get("reset_otp_expires")

            try:
                expires_at = datetime.fromisoformat(expires_raw) if expires_raw else None
                if expires_at and expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                expires_at = None

            if not expires_at or datetime.now(timezone.utc) > expires_at:
                session["reset_step"] = "request"
                flash("OTP expired. Please request a new OTP.", "danger")

                return redirect(url_for("forgot_password"))

            if entered_otp != session.get("reset_otp"):
                flash("Invalid OTP. Please try again.", "danger")

                return redirect(url_for("forgot_password"))

            session["reset_step"] = "reset"
            flash("OTP verified. Set your new password.", "success")

            return redirect(url_for("forgot_password"))

        if action == "reset_password":
            password = request.form.get("password", "")
            confirm = request.form.get("confirm", "")
            email = session.get("reset_email")

            if session.get("reset_step") != "reset" or not email:
                flash("Please verify OTP first.", "danger")

                return redirect(url_for("forgot_password"))

            if password != confirm:
                flash("Passwords do not match!", "danger")

                return redirect(url_for("forgot_password"))

            user = db.session.execute(
                db.select(User).filter_by(email=email)
            ).scalar_one_or_none()

            if not user:
                flash("Email not found!", "danger")

                return redirect(url_for("forgot_password"))

            user.password = bcrypt.generate_password_hash(password).decode("utf-8")

            db.session.commit()

            session.pop("reset_email", None)
            session.pop("reset_otp", None)
            session.pop("reset_otp_expires", None)
            session.pop("reset_step", None)

            flash("Password updated successfully! Please login.", "success")

            return redirect(url_for("login"))

    return render_template("forgot_password.html", step=step)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

    if request.method == "POST":

        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        risk_profile = request.form.get("risk_profile", "Moderate").strip()
        investment_goal = request.form.get("investment_goal", "").strip()
        preferred_market = request.form.get("preferred_market", "NSE").strip()

        if not full_name or not email:
            flash("Name and email are required.", "danger")

            return redirect(url_for("profile"))

        existing_user = User.query.filter(
            User.email == email,
            User.id != current_user.id,
        ).first()

        if existing_user:
            flash("This email is already used by another account.", "danger")

            return redirect(url_for("profile"))

        current_user.full_name = full_name
        current_user.email = email
        current_user.phone = phone
        current_user.risk_profile = risk_profile
        current_user.investment_goal = investment_goal
        current_user.preferred_market = preferred_market

        db.session.commit()

        flash("Profile updated successfully.", "success")

        return redirect(url_for("profile"))

    return render_template("profile.html", active_panel="profile")


@app.route("/settings")
@login_required
def settings():

    return render_template("profile.html", active_panel="settings")


@app.route("/compare")
@login_required
def compare():
    return render_template("compare.html")


@app.route("/compare-results")
@login_required
def compare_results():

    symbols_string = request.args.get("symbols", "")

    symbols = [
        symbol.strip().upper() for symbol in symbols_string.split(",") if symbol.strip()
    ]

    # Minimum 2 stocks required
    if len(symbols) < 2:
        return redirect(url_for("compare"))

    # Maximum 3 stocks allowed
    symbols = symbols[:3]

    comparison_data = []

    # Historical chart data
    chart_data = {
        "1M": [],
        "6M": [],
        "1Y": [],
        "3Y": [],
        "5Y": [],
    }

    # Yahoo Finance periods
    chart_periods = {
        "1M": "1mo",
        "6M": "6mo",
        "1Y": "1y",
        "3Y": "3y",
        "5Y": "5y",
    }

    for symbol in symbols:
        try:
            # Convert symbol into NSE ticker
            clean_symbol = symbol.replace(".NS", "").strip().upper()

            ticker_symbol = f"{clean_symbol}.NS"

            print(
                "Fetching comparison ticker:",
                ticker_symbol,
            )

            ticker = yf.Ticker(ticker_symbol)

            try:
                info = ticker.info or {}
            except Exception as info_error:
                print(f"Comparison metadata error for {clean_symbol}:", info_error)
                info = {}

            # Get latest stock price
            latest_history = ticker.history(period="5d")

            latest_price = "N/A"

            if not latest_history.empty and "Close" in latest_history.columns:
                close_prices = latest_history["Close"].dropna()

                if not close_prices.empty:
                    latest_price = round(
                        float(close_prices.iloc[-1]),
                        2,
                    )

            # =================================
            # COMPANY INFORMATION
            # =================================

            stock_data = {
                "symbol": clean_symbol,
                "name": (info.get("longName") or info.get("shortName") or clean_symbol),
                "price": latest_price,
                "market_cap": (info.get("marketCap") or "N/A"),
                "pe_ratio": (info.get("trailingPE") or "N/A"),
                "eps": (info.get("trailingEps") or "N/A"),
                "revenue": (info.get("totalRevenue") or "N/A"),
                "roe": (info.get("returnOnEquity") or "N/A"),
                "dividend_yield": (
                    round(float(info.get("dividendYield")) * 100, 2)
                    if info.get("dividendYield") is not None
                    else "N/A"
                ),

                "sector": (info.get("sector") or "N/A"),
                "industry": (info.get("industry") or "N/A"),
                "website": (info.get("website") or "N/A"),
                "description": (
                    info.get("longBusinessSummary")
                    or ("Company information is currently unavailable.")
                ),
            }

            comparison_data.append(stock_data)

            # =================================
            # HISTORICAL PRICE DATA
            # =================================

            for range_name, yahoo_period in chart_periods.items():
                try:
                    historical_data = ticker.history(
                        period=yahoo_period,
                        auto_adjust=False,
                    )

                    dates = []
                    prices = []

                    if not historical_data.empty and "Close" in historical_data.columns:
                        historical_data = historical_data.dropna(
                            subset=["Close"]
                        ).sort_index()

                        for date, row in historical_data.iterrows():
                            dates.append(date.strftime("%Y-%m-%d"))
                            prices.append(round(float(row["Close"]), 2))

                    chart_data[range_name].append(
                        {
                            "symbol": clean_symbol,
                            "name": stock_data["name"],
                            "dates": dates,
                            "prices": prices,
                        }
                    )

                except Exception as chart_error:
                    print(
                        f"Historical chart error for {clean_symbol} {range_name}:",
                        chart_error,
                    )

                    chart_data[range_name].append(
                        {
                            "symbol": clean_symbol,
                            "name": stock_data["name"],
                            "dates": [],
                            "prices": [],
                        }
                    )

        except Exception as error:
            print(f"Comparison data error for {symbol}:", error)
            comparison_data.append(
                {
                    "symbol": symbol,
                    "name": symbol,
                    "price": "N/A",
                    "market_cap": "N/A",
                    "pe_ratio": "N/A",
                    "eps": "N/A",
                    "revenue": "N/A",
                    "roe": "N/A",
                    "dividend_yield": "N/A",
                    "sector": "N/A",
                    "industry": "N/A",
                    "website": "N/A",
                    "description": "Company information is currently unavailable.",
                }
            )

    return render_template(
        "compare_results.html",
        stocks=comparison_data,
        chart_data=chart_data,
    )


@app.route("/watchlist")
@login_required
def watchlist():

    stocks = Watchlist.query.filter_by(user_id=current_user.id).all()

    return render_template("watchlist.html", stocks=stocks)


@app.route("/watchlist/add", methods=["POST"])
@login_required
def add_to_watchlist():
    data = request.get_json(silent=True) or request.form or {}
    try:
        symbol = validate_stock_symbol(data.get("symbol"))
    except ValueError as ve:
        return jsonify({"success": False, "message": str(ve)}), 400

    exists = Watchlist.query.filter_by(user_id=current_user.id, symbol=symbol).first()
    if exists:
        return jsonify({"success": False, "message": "Already added"})

    stock = Watchlist(user_id=current_user.id, symbol=symbol)
    try:
        db.session.add(stock)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"success": False, "message": "Already added"})

    return jsonify({"success": True})


@app.route("/watchlist/remove", methods=["POST"])
@login_required
def remove_from_watchlist():
    data = request.get_json(silent=True) or request.form or {}
    try:
        symbol = validate_stock_symbol(data.get("symbol"))
    except ValueError as ve:
        return jsonify({"success": False, "message": str(ve)}), 400

    stock = Watchlist.query.filter_by(user_id=current_user.id, symbol=symbol).first()
    if stock:
        db.session.delete(stock)
        db.session.commit()

    return jsonify({"success": True})


@app.route("/api/watchlist-summary")
@login_required
def watchlist_summary():

    try:
        watchlist = Watchlist.query.filter_by(user_id=current_user.id).all()

        symbols = [stock.symbol for stock in watchlist]

        summary = StockService.get_watchlist_summary(symbols)

        return jsonify(summary)

    except Exception as e:

        print("Watchlist Summary Error:", e)

        return jsonify(
            {
                "holdings": 0,
                "gainers": 0,
                "losers": 0,
                "avg_return": 0,
                "allocation": [],
                "stocks": [],
            }
        )


@app.route("/api/notifications")
@login_required
def notifications():
    """Return a small, fresh set of market notifications for the navbar."""
    try:
        watchlist_symbols = [
            item.symbol.upper()
            for item in Watchlist.query.filter_by(user_id=current_user.id)
            .order_by(Watchlist.created_at.desc())
            .limit(3)
            .all()
        ]
        symbols = ["^NSEI"] + (watchlist_symbols or ["^BSESN"])
        items = []

        for symbol in symbols:
            try:
                history = yf.Ticker(symbol).history(period="5d", auto_adjust=False)
                history = history.dropna(subset=["Close"])
                if history.empty:
                    continue

                current = float(history["Close"].iloc[-1])
                previous = float(history["Close"].iloc[-2]) if len(history) > 1 else current
                change = ((current - previous) / previous * 100) if previous else 0
                label = (
                    "NIFTY 50" if symbol == "^NSEI"
                    else "SENSEX" if symbol == "^BSESN"
                    else symbol.replace(".NS", "")
                )
                direction = "up" if change >= 0 else "down"
                items.append({
                    "id": symbol,
                    "title": f"{label} is {direction} {abs(change):.2f}% today",
                    "detail": f"Live price: ₹{current:,.2f}",
                    "type": direction,
                    "time": "Live now",
                })
            except Exception as error:
                print(f"Notification price error for {symbol}: {error}")

        return jsonify({"success": True, "notifications": items, "updated_at": datetime.now().strftime("%I:%M %p")})
    except Exception as error:
        print("Notification Error:", error)
        return jsonify({"success": False, "notifications": [], "message": "Unable to load live notifications"}), 500


@app.route("/api/stock-live/<symbol>")
@login_required
def stock_live(symbol):

    try:

        if "." not in symbol:
            symbol = f"{symbol.upper()}.NS"
        else:
            symbol = symbol.upper()

        stock = yf.Ticker(symbol)

        try:
            info = stock.info or {}
        except Exception:
            info = {}

        try:
            fast_info = stock.fast_info or {}
        except Exception:
            fast_info = {}

        history = stock.history(period="5d")

        history = history.dropna(subset=["Close"])

        current = fast_info.get("lastPrice")

        if history.empty and not current:
            raise Exception("No price data")

        current = float(current or history["Close"].iloc[-1])

        previous = float(history["Close"].iloc[-2]) if len(history) >= 2 else current

        change = round(((current - previous) / previous) * 100, 2)

        return jsonify(
            {
                "company": info.get("longName", symbol),
                "price": f"{current:,.2f}",
                "change": change,
                "market_cap": info.get("marketCap"),
                "pe": info.get("trailingPE"),
                "high52": info.get("fiftyTwoWeekHigh"),
                "low52": info.get("fiftyTwoWeekLow"),
            }
        )

    except Exception as error:
        print("Live Stock Error:", error)

        return jsonify(
            {
                "company": symbol,
                "price": "--",
                "change": 0,
                "market_cap": "--",
                "pe": "--",
                "high52": "--",
                "low52": "--",
            }
        )


@app.route("/dashboard-market")
@login_required
def dashboard_market():

    market = StockService.get_market_data()

    return jsonify(
        {
            "nifty": market["nifty"],
            "sensex": market["sensex"],
            "nifty_change": market["status"],
            "sensex_change": market["status"],
        }
    )


@app.route("/api/dashboard-market-chart")
@login_required
def dashboard_market_chart():

    period = request.args.get("period", "6mo")

    chart = StockService.get_market_chart(period)

    if not chart:
        return jsonify(
            {
                "success": False,
                "message": "Unable to load market chart.",
            }
        ), 503

    return jsonify(
        {
            "success": True,
            "chart_html": chart,
        }
    )


# ==================================================
# RUN APPLICATION
# ==================================================


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
