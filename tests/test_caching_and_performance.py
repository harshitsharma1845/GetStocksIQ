import unittest
import time
from unittest.mock import patch, MagicMock
from threading import Thread

from app import app
from database.models import User
from services.cache_service import CacheService
from services.news_service import NewsService
from services.stock_service import StockService
from services.portfolio_service import PortfolioService


class TestCachingAndPerformance(unittest.TestCase):

    def setUp(self):
        CacheService.clear()

    def tearDown(self):
        CacheService.clear()

    def test_cache_set_get_and_expiration(self):
        """Verify standard cache set, hit, and expiration."""
        CacheService.set("test_key", {"price": 100}, ttl_seconds=1)
        # Fresh hit
        self.assertEqual(CacheService.get("test_key"), {"price": 100})
        # Wait for expiration
        time.sleep(1.1)
        # Expired with allow_stale=False should return None
        self.assertIsNone(CacheService.get("test_key", allow_stale=False))

    def test_cache_stale_fallback(self):
        """Verify expired entries can be served with allow_stale=True."""
        CacheService.set("stale_test", "original_value", ttl_seconds=1)
        time.sleep(1.1)
        # allow_stale=False gives None
        self.assertIsNone(CacheService.get("stale_test", allow_stale=False))
        # allow_stale=True gives original_value
        self.assertEqual(CacheService.get("stale_test", allow_stale=True), "original_value")

    def test_cache_get_with_meta(self):
        """Verify FRESH, STALE, and MISS statuses."""
        val, status, created = CacheService.get_with_meta("non_existent")
        self.assertEqual(status, "MISS")
        self.assertIsNone(val)

        CacheService.set("meta_key", "meta_val", ttl_seconds=1)
        val, status, created = CacheService.get_with_meta("meta_key")
        self.assertEqual(status, "FRESH")
        self.assertEqual(val, "meta_val")
        self.assertIsNotNone(created)

        time.sleep(1.1)
        val, status, created = CacheService.get_with_meta("meta_key", allow_stale=True)
        self.assertEqual(status, "STALE")
        self.assertEqual(val, "meta_val")

    def test_symbol_normalization(self):
        """Verify symbol normalization across variations and index aliases."""
        self.assertEqual(CacheService.normalize_symbol("reliance"), "RELIANCE.NS")
        self.assertEqual(CacheService.normalize_symbol("RELIANCE.NS"), "RELIANCE.NS")
        self.assertEqual(CacheService.normalize_symbol("  tcs.ns?  "), "TCS.NS")
        self.assertEqual(CacheService.normalize_symbol("NIFTY 50"), "^NSEI")
        self.assertEqual(CacheService.normalize_symbol("nifty"), "^NSEI")
        self.assertEqual(CacheService.normalize_symbol("SENSEX"), "^BSESN")
        self.assertEqual(CacheService.normalize_symbol("bse"), "^BSESN")

    def test_stampede_protection_concurrent_get_or_set(self):
        """Verify simultaneous calls to get_or_set invoke the underlying fetch_fn only once."""
        call_count = [0]

        def expensive_fetch():
            time.sleep(0.1) # Simulate slow network call
            call_count[0] += 1
            return {"data": "expensive"}

        threads = []
        results = [None] * 5

        def worker(idx):
            results[idx] = CacheService.get_or_set("stampede_key", expensive_fetch, ttl_seconds=60)

        for i in range(5):
            t = Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All 5 threads should receive identical data
        for r in results:
            self.assertEqual(r, {"data": "expensive"})

        # Expensive fetch should have been executed exactly once
        self.assertEqual(call_count[0], 1)

    def test_get_or_set_stale_fallback_on_exception(self):
        """Verify get_or_set returns last valid stale data when fetch_fn raises an exception."""
        # Initial successful set
        CacheService.set("fail_key", {"status": "ok"}, ttl_seconds=1)
        time.sleep(1.1)

        def failing_fetch():
            raise ConnectionError("External API down")

        result = CacheService.get_or_set("fail_key", failing_fetch, ttl_seconds=60, allow_stale=True)
        self.assertEqual(result, {"status": "ok"})

    def test_news_service_caching_and_mocked_rss(self):
        """Verify NewsService caches results and does not make duplicate HTTP calls."""
        fake_feed = MagicMock()
        fake_feed.entries = [
            {"title": "Reliance Q3 profit jumps 15%", "link": "https://example.com/1", "published": "Today"}
        ]

        with patch("feedparser.parse", return_value=fake_feed) as mock_parse:
            # First call -> triggers parse
            articles1 = NewsService.get_stock_news("RELIANCE.NS")
            self.assertEqual(len(articles1), 1)
            self.assertEqual(mock_parse.call_count, 1)

            # Second call -> served from cache, no network call
            articles2 = NewsService.get_stock_news("RELIANCE.NS")
            self.assertEqual(len(articles2), 1)
            self.assertEqual(mock_parse.call_count, 1) # Still 1

    def test_news_service_failure_returns_empty_not_fake(self):
        """Verify NewsService returns empty list on network failure when no cache exists (no fake news)."""
        with patch("feedparser.parse", side_effect=Exception("Timeout")):
            articles = NewsService.get_stock_news("NONEXISTENT_XYZ")
            self.assertEqual(articles, [])

    def test_market_data_indices_caching(self):
        """Verify StockService.get_market_data caches index values."""
        fake_ticker = MagicMock()
        fake_ticker.fast_info = {"lastPrice": 24500.50}

        with patch("yfinance.Ticker", return_value=fake_ticker) as mock_yf:
            data1 = StockService.get_market_data()
            self.assertIn("24,500.50", data1["nifty"])
            initial_yf_calls = mock_yf.call_count

            # Second call should use cache
            data2 = StockService.get_market_data()
            self.assertEqual(mock_yf.call_count, initial_yf_calls)
            self.assertEqual(data1, data2)

    def test_user_cache_isolation(self):
        """Verify user portfolios are NOT cached globally across users."""
        with app.app_context():
            user1 = User.query.first()
            if user1:
                p1 = PortfolioService.get_or_create_portfolio(user1.id)
                summary1 = PortfolioService.get_portfolio_summary(p1.id)
                # Verify that no global key 'user_portfolio' or 'portfolio_summary' is in CacheService
                self.assertIsNone(CacheService.get("portfolio_summary"))
                self.assertIsNone(CacheService.get(f"portfolio_summary_{user1.id}"))


if __name__ == "__main__":
    unittest.main()
