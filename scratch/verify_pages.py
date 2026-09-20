import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from database.models import User
from flask_bcrypt import Bcrypt

app.config["TESTING"] = True
app.config["WTF_CSRF_ENABLED"] = False

with app.app_context():
    db.create_all()
    user = User.query.filter_by(email="verifier@test.com").first()
    if not user:
        bcrypt = Bcrypt(app)
        user = User(
            full_name="Endpoint Verifier",
            email="verifier@test.com",
            password=bcrypt.generate_password_hash("password123").decode("utf-8")
        )
        db.session.add(user)
        db.session.commit()
    user_id = user.id

anon_client = app.test_client()
auth_client = app.test_client()

# Create authenticated session
with auth_client.session_transaction() as sess:
    sess["_user_id"] = str(user_id)
    sess["_fresh"] = True

print("=" * 60, flush=True)
print("COMPREHENSIVE ENDPOINT & PAGE VERIFICATION RUNNER", flush=True)
print("=" * 60, flush=True)

endpoints = [
    # Public & Auth Routes (Anonymous Client)
    ("GET", "/login", None, "Login Page", False),
    ("GET", "/register", None, "Registration Page", False),
    ("GET", "/forgot-password", None, "Password Recovery Page", False),
    # Core Authenticated Pages (Authenticated Client)
    ("GET", "/dashboard", None, "Dashboard Page", True),
    ("GET", "/portfolio", None, "Portfolio Page", True),
    ("GET", "/watchlist", None, "Watchlist Page", True),
    ("GET", "/compare", None, "Compare Page", True),
    ("GET", "/compare-results?symbols=TCS.NS,INFY.NS", None, "Comparison Results View", True),
    ("GET", "/analysis?symbol=RELIANCE.NS", None, "Stock Analysis Page", True),
    ("GET", "/profile", None, "User Profile Page", True),
    # Critical API Endpoints
    ("GET", "/api/search-stocks?q=TCS", None, "Stock Search Autocomplete API", True),
    ("POST", "/api/ask-ai", {"question": "What is the P/E ratio?"}, "Conversational AI Assistant API", True),
    ("POST", "/api/portfolio/ai-analysis", {}, "Portfolio AI Health Analysis API", True),
]

all_passed = True
total_checked = 0
total_passed = 0
total_failed = 0

for method, url, body, desc, auth_required in endpoints:
    total_checked += 1
    client = auth_client if auth_required else anon_client
    if method == "GET":
        res = client.get(url)
    else:
        res = client.post(url, json=body or {})

    status = res.status_code
    passed = (status == 200)
    if not passed:
        all_passed = False
        total_failed += 1
        print(f"  [FAIL] {method:4} {url:<45} -> HTTP {status} ({desc})", flush=True)
    else:
        total_passed += 1
        print(f"  [PASS] {method:4} {url:<45} -> HTTP {status} ({desc})", flush=True)

print("=" * 60, flush=True)
print(f"RESULTS: {total_passed}/{total_checked} ENDPOINTS PASSED (Failed: {total_failed})", flush=True)
print("=" * 60, flush=True)

if not all_passed:
    sys.exit(1)
