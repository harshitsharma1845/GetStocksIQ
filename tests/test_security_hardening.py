import unittest
import os
import json
import uuid
from decimal import Decimal

os.environ["SECRET_KEY"] = "test-secret-key-security-hardening"

from app import app, db, validate_stock_symbol, validate_trade_inputs, get_csrf_token
from database.models import User, Portfolio, Holding, Transaction, Watchlist
from flask_bcrypt import Bcrypt


class TestSecurityHardening(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = True
        self.client = self.app.test_client()

        self.app_context = self.app.app_context()
        self.app_context.push()

        db.session.remove()
        db.drop_all()
        db.create_all()

        bcrypt = Bcrypt(self.app)
        uid = str(uuid.uuid4())[:8]

        # Create User A
        self.user_a = User(
            full_name="Alice Trader",
            email=f"alice_{uid}@sec.com",
            password=bcrypt.generate_password_hash("Password123!").decode("utf-8"),
        )
        # Create User B
        self.user_b = User(
            full_name="Bob Attacker",
            email=f"bob_{uid}@sec.com",
            password=bcrypt.generate_password_hash("Password123!").decode("utf-8"),
        )
        db.session.add_all([self.user_a, self.user_b])
        db.session.commit()

        self.user_a_id = self.user_a.id
        self.user_b_id = self.user_b.id

        # Create User A's portfolio and a holding
        self.portfolio_a = Portfolio(user_id=self.user_a_id, name="Alice Portfolio")
        db.session.add(self.portfolio_a)
        db.session.commit()

        self.holding_a = Holding(
            portfolio_id=self.portfolio_a.id,
            symbol="RELIANCE.NS",
            stock_name="Reliance Industries",
            quantity=10.0,
            average_buy_price=2500.0,
        )
        db.session.add(self.holding_a)
        db.session.commit()
        self.holding_a_id = self.holding_a.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login_as(self, client, user_id):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user_id)
            sess["_fresh"] = True
            sess["csrf_token"] = "valid-test-csrf-token-32chars-ok"
        return "valid-test-csrf-token-32chars-ok"

    # =========================================================================
    # 1. CSRF PROTECTION TESTS
    # =========================================================================

    def test_csrf_missing_token_rejected_on_post(self):
        """Verify state-changing POST without CSRF token is rejected with HTTP 403."""
        client = self.app.test_client()
        self._login_as(client, self.user_a_id)

        # POST without CSRF token header or body
        res = client.post(
            "/api/portfolio/buy",
            json={"symbol": "INFY.NS", "quantity": 5, "price": 1500.0},
        )
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("CSRF", data["message"])

    def test_csrf_invalid_token_rejected_on_post(self):
        """Verify state-changing POST with invalid CSRF token is rejected with HTTP 403."""
        client = self.app.test_client()
        self._login_as(client, self.user_a_id)

        res = client.post(
            "/api/portfolio/buy",
            json={"symbol": "INFY.NS", "quantity": 5, "price": 1500.0},
            headers={"X-CSRF-Token": "completely-invalid-attacker-csrf-token"},
        )
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertFalse(data["success"])

    def test_csrf_valid_token_accepted_via_header(self):
        """Verify state-changing POST with valid CSRF header succeeds."""
        client = self.app.test_client()
        csrf_token = self._login_as(client, self.user_a_id)

        res = client.post(
            "/watchlist/add",
            json={"symbol": "TCS.NS"},
            headers={"X-CSRF-Token": csrf_token},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])

    def test_csrf_get_requests_unaffected(self):
        """Verify safe GET requests do not require CSRF tokens."""
        client = self.app.test_client()
        self._login_as(client, self.user_a_id)

        res = client.get("/profile")
        self.assertEqual(res.status_code, 200)

    # =========================================================================
    # 2. SESSION & COOKIE SECURITY TESTS
    # =========================================================================

    def test_session_cookie_security_config(self):
        """Verify session cookie flags (HttpOnly, SameSite)."""
        self.assertTrue(self.app.config.get("SESSION_COOKIE_HTTPONLY"))
        self.assertEqual(self.app.config.get("SESSION_COOKIE_SAMESITE"), "Lax")
        self.assertTrue(self.app.config.get("REMEMBER_COOKIE_HTTPONLY"))
        self.assertEqual(self.app.config.get("REMEMBER_COOKIE_SAMESITE"), "Lax")
        self.assertEqual(self.app.config.get("MAX_CONTENT_LENGTH"), 16 * 1024 * 1024)

    # =========================================================================
    # 3. HTTP SECURITY HEADERS TESTS
    # =========================================================================

    def test_security_headers_present_on_all_responses(self):
        """Verify X-Content-Type-Options, X-Frame-Options, Referrer-Policy, CSP are returned."""
        res = self.client.get("/login")
        self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res.headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertEqual(res.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertIn("default-src 'self'", res.headers.get("Content-Security-Policy", ""))
        self.assertIn("cdn.jsdelivr.net", res.headers.get("Content-Security-Policy", ""))
        self.assertIn("cdn.plot.ly", res.headers.get("Content-Security-Policy", ""))

    def test_hsts_header_in_secure_mode(self):
        """Verify Strict-Transport-Security header is applied when HTTPS is simulated."""
        self.app.config["SESSION_COOKIE_SECURE"] = True
        try:
            res = self.client.get("/login")
            self.assertIn("max-age=31536000", res.headers.get("Strict-Transport-Security", ""))
        finally:
            self.app.config["SESSION_COOKIE_SECURE"] = False

    # =========================================================================
    # 4. INPUT VALIDATION TESTS
    # =========================================================================

    def test_validate_stock_symbol_allowed_characters(self):
        """Verify valid market tickers pass and invalid characters/payloads are rejected."""
        # Valid tickers
        self.assertEqual(validate_stock_symbol("RELIANCE.NS"), "RELIANCE.NS")
        self.assertEqual(validate_stock_symbol("tcs.ns"), "TCS.NS")
        self.assertEqual(validate_stock_symbol("500325.BO"), "500325.BO")
        self.assertEqual(validate_stock_symbol("^NSEI"), "^NSEI")

        # Invalid tickers (XSS, path traversal, shell characters, spaces, empty)
        with self.assertRaises(ValueError):
            validate_stock_symbol("<script>alert(1)</script>")
        with self.assertRaises(ValueError):
            validate_stock_symbol("../../etc/passwd")
        with self.assertRaises(ValueError):
            validate_stock_symbol("RELIANCE; DROP TABLE USERS;--")
        with self.assertRaises(ValueError):
            validate_stock_symbol("TOOLONGTICKERNAMEEXCEEDINGTWENTYCHARS.NS")
        with self.assertRaises(ValueError):
            validate_stock_symbol("")
        with self.assertRaises(ValueError):
            validate_stock_symbol(None)

    def test_validate_trade_inputs_bounds(self):
        """Verify trade input validation enforces positive ranges, reject NaN/Infinity/negatives."""
        # Valid trade inputs
        q, p, f = validate_trade_inputs(10, 2500.50, 20.0)
        self.assertEqual(q, 10.0)
        self.assertEqual(p, 2500.50)
        self.assertEqual(f, 20.0)

        # Invalid quantities
        with self.assertRaises(ValueError):
            validate_trade_inputs(0, 100)  # Zero quantity
        with self.assertRaises(ValueError):
            validate_trade_inputs(-5, 100)  # Negative quantity
        with self.assertRaises(ValueError):
            validate_trade_inputs(2_000_000, 100)  # Excessive quantity
        with self.assertRaises(ValueError):
            validate_trade_inputs("not-a-number", 100)

        # Invalid prices
        with self.assertRaises(ValueError):
            validate_trade_inputs(10, 0)  # Zero price
        with self.assertRaises(ValueError):
            validate_trade_inputs(10, -50.0)  # Negative price
        with self.assertRaises(ValueError):
            validate_trade_inputs(10, 50_000_000.0)  # Excessive price
        with self.assertRaises(ValueError):
            validate_trade_inputs(10, float("nan"))  # NaN
        with self.assertRaises(ValueError):
            validate_trade_inputs(10, float("inf"))  # Infinity

        # Invalid fees
        with self.assertRaises(ValueError):
            validate_trade_inputs(10, 100, -5.0)  # Negative fees
        with self.assertRaises(ValueError):
            validate_trade_inputs(10, 100, 500_000.0)  # Excessive fees

    def test_ai_query_input_length_validation(self):
        """Verify oversized AI queries (>1,000 chars) are rejected with HTTP 400."""
        client = self.app.test_client()
        csrf_token = self._login_as(client, self.user_a_id)

        oversized_query = "What is " + ("A" * 1050)
        res = client.post(
            "/api/ask-ai",
            json={"question": oversized_query},
            headers={"X-CSRF-Token": csrf_token},
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("too long", data["message"])

    # =========================================================================
    # 5. OBJECT-LEVEL AUTHORIZATION & CROSS-USER ISOLATION TESTS
    # =========================================================================

    def test_user_b_cannot_delete_user_a_holding(self):
        """Verify User B cannot delete or access User A's holding (IDOR protection)."""
        client = self.app.test_client()
        csrf_token = self._login_as(client, self.user_b_id)

        # User B attempts to delete User A's holding
        res = client.delete(
            f"/api/portfolio/holding/{self.holding_a_id}",
            headers={"X-CSRF-Token": csrf_token},
        )
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertFalse(data["success"])

        # Confirm holding still exists in database
        holding = db.session.get(Holding, self.holding_a_id)
        self.assertIsNotNone(holding)

    def test_user_b_cannot_sell_user_a_holding(self):
        """Verify User B cannot sell shares from User A's portfolio."""
        client = self.app.test_client()
        csrf_token = self._login_as(client, self.user_b_id)

        # User B attempts to sell RELIANCE.NS which they do not own
        res = client.post(
            "/api/portfolio/sell",
            json={"symbol": "RELIANCE.NS", "quantity": 5, "price": 2600.0},
            headers={"X-CSRF-Token": csrf_token},
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("insufficient shares", data["message"].lower())

    # =========================================================================
    # 6. SAFE ERROR HANDLING & INFORMATION DISCLOSURE TESTS
    # =========================================================================

    def test_404_error_response_is_safe_and_clean(self):
        """Verify 404 handler returns clean message without leaking stack trace or file paths."""
        res = self.client.get("/api/non-existent-endpoint-xyz")
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertNotIn("Traceback", json.dumps(data))
        self.assertNotIn("database.db", json.dumps(data))
        self.assertNotIn("d:\\", json.dumps(data).lower())

    def test_405_method_not_allowed_is_safe(self):
        """Verify 405 handler returns clean JSON on API routes with valid CSRF."""
        client = self.app.test_client()
        csrf_token = self._login_as(client, self.user_a_id)
        res = client.post(
            "/api/search-stocks",
            headers={"X-CSRF-Token": csrf_token},
        )
        self.assertEqual(res.status_code, 405)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("not allowed", data["message"].lower())


if __name__ == "__main__":
    unittest.main()
