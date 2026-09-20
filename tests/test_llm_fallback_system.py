import unittest
import os
import json
from unittest.mock import patch, MagicMock
import requests

from services.llm_service import LLMService, VerifiedContextBuilder


class TestLLMFallbackSystem(unittest.TestCase):

    def setUp(self):
        # Clear any environment overrides before each test
        os.environ.pop("LLM_PRIMARY_MODEL", None)
        os.environ.pop("LLM_FALLBACK_MODELS", None)
        os.environ.pop("LLM_TIMEOUT", None)
        os.environ.pop("LLM_MAX_RETRIES", None)

    def tearDown(self):
        os.environ.pop("LLM_PRIMARY_MODEL", None)
        os.environ.pop("LLM_FALLBACK_MODELS", None)
        os.environ.pop("LLM_TIMEOUT", None)
        os.environ.pop("LLM_MAX_RETRIES", None)

    def test_duplicate_models_are_removed(self):
        """Verify model pipeline deduplication preserves order without duplicate entries."""
        os.environ["LLM_PRIMARY_MODEL"] = "model-A"
        os.environ["LLM_FALLBACK_MODELS"] = "model-B, model-A, model-C, model-B, "

        pipeline = LLMService.get_model_pipeline()
        self.assertEqual(pipeline, ["model-A", "model-B", "model-C"])

    def test_missing_api_key_skips_network(self):
        """Verify missing API key executes zero network requests and returns safe configuration error."""
        with patch("services.llm_service.LLMService.get_api_key", return_value=None):
            with patch("requests.post") as mock_post:
                res = LLMService.execute_completion([{"role": "user", "content": "Hi"}])
                self.assertFalse(res["success"])
                self.assertEqual(res["error_category"], "configuration_error")
                self.assertFalse(mock_post.called)

                # Test public methods return deterministic fallback
                ans = LLMService.ask_financial_assistant("What is P/E?")
                self.assertTrue(ans["success"])
                self.assertIn("GetStockIQ Assistant (Offline Mode)", ans["answer"])

    def test_primary_succeeds_immediately(self):
        """Verify fast-path: primary model succeeds on first attempt and makes exactly ONE request."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Reliance is a diversified conglomerate."}}]
        }

        with patch("services.llm_service.LLMService.get_api_key", return_value="fake-api-key"):
            with patch("requests.post", return_value=mock_resp) as mock_post:
                messages = [{"role": "user", "content": "Analyze RELIANCE"}]
                res = LLMService.execute_completion(messages)

                self.assertTrue(res["success"])
                self.assertEqual(res["content"], "Reliance is a diversified conglomerate.")
                self.assertEqual(res["model_used"], "openai/gpt-4o-mini")
                self.assertEqual(res["retries"], 0)
                self.assertEqual(res["attempts"], 1)
                self.assertFalse(res["fallback_used"])
                self.assertEqual(mock_post.call_count, 1)

    def test_success_does_not_call_fallback_models(self):
        """Verify no fallback models are contacted after a successful primary response."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "TCS is an IT leader."}}]
        }

        with patch("services.llm_service.LLMService.get_api_key", return_value="fake-api-key"):
            with patch("requests.post", return_value=mock_resp) as mock_post:
                explanation = LLMService.generate_stock_explanation(
                    "TCS.NS",
                    {"name": "Tata Consultancy Services", "price": 4100},
                    {"overall_score": 85, "signal": "BUY", "risk_label": "Low Risk", "factor_scores": {}}
                )

                self.assertEqual(explanation, "TCS is an IT leader.")
                self.assertEqual(mock_post.call_count, 1)

    def test_primary_timeout_triggers_retry_and_fallback(self):
        """Verify transient timeout retries primary once, then falls back to secondary model."""
        os.environ["LLM_PRIMARY_MODEL"] = "primary-model"
        os.environ["LLM_FALLBACK_MODELS"] = "fallback-model"
        os.environ["LLM_MAX_RETRIES"] = "1"

        success_resp = MagicMock()
        success_resp.status_code = 200
        success_resp.json.return_value = {
            "choices": [{"message": {"content": "Fallback model response"}}]
        }

        # Primary attempt 1: Timeout, Primary attempt 2: Timeout, Fallback attempt 1: Success
        side_effects = [
            requests.exceptions.Timeout("Read timeout"),
            requests.exceptions.Timeout("Read timeout"),
            success_resp
        ]

        with patch("services.llm_service.LLMService.get_api_key", return_value="fake-api-key"):
            with patch("time.sleep"):  # Mock sleep to run instantly
                with patch("requests.post", side_effect=side_effects) as mock_post:
                    res = LLMService.execute_completion([{"role": "user", "content": "Test"}])

                    self.assertTrue(res["success"])
                    self.assertEqual(res["content"], "Fallback model response")
                    self.assertEqual(res["model_used"], "fallback-model")
                    self.assertTrue(res["fallback_used"])
                    self.assertEqual(mock_post.call_count, 3)

    def test_primary_rate_limited_triggers_fallback(self):
        """Verify 429 rate limit response triggers backoff retry and falls back upon exhaustion."""
        os.environ["LLM_PRIMARY_MODEL"] = "primary-model"
        os.environ["LLM_FALLBACK_MODELS"] = "fallback-model"
        os.environ["LLM_MAX_RETRIES"] = "1"

        rate_limit_resp = MagicMock()
        rate_limit_resp.status_code = 429
        rate_limit_resp.headers = {"Retry-After": "0.1"}

        success_resp = MagicMock()
        success_resp.status_code = 200
        success_resp.json.return_value = {
            "choices": [{"message": {"content": "Success after 429 fallback"}}]
        }

        side_effects = [
            rate_limit_resp,  # Primary attempt 1
            rate_limit_resp,  # Primary retry 1
            success_resp      # Fallback attempt 1
        ]

        with patch("services.llm_service.LLMService.get_api_key", return_value="fake-api-key"):
            with patch("time.sleep"):
                with patch("requests.post", side_effect=side_effects) as mock_post:
                    res = LLMService.execute_completion([{"role": "user", "content": "Test"}])

                    self.assertTrue(res["success"])
                    self.assertEqual(res["model_used"], "fallback-model")
                    self.assertTrue(res["fallback_used"])
                    self.assertEqual(mock_post.call_count, 3)

    def test_permanent_auth_error_skips_retries(self):
        """Verify 401 auth error does not waste retries on the same model."""
        os.environ["LLM_PRIMARY_MODEL"] = "primary-model"
        os.environ["LLM_FALLBACK_MODELS"] = "fallback-model"
        os.environ["LLM_MAX_RETRIES"] = "2"

        auth_error_resp = MagicMock()
        auth_error_resp.status_code = 401
        auth_error_resp.headers = {}

        success_resp = MagicMock()
        success_resp.status_code = 200
        success_resp.json.return_value = {
            "choices": [{"message": {"content": "Success from fallback"}}]
        }

        # Primary attempt 1: 401 (skips retry), Fallback attempt 1: 200 OK
        side_effects = [
            auth_error_resp,
            success_resp
        ]

        with patch("services.llm_service.LLMService.get_api_key", return_value="fake-api-key"):
            with patch("time.sleep") as mock_sleep:
                with patch("requests.post", side_effect=side_effects) as mock_post:
                    res = LLMService.execute_completion([{"role": "user", "content": "Test"}])

                    self.assertTrue(res["success"])
                    self.assertEqual(res["model_used"], "fallback-model")
                    self.assertEqual(mock_post.call_count, 2)
                    self.assertFalse(mock_sleep.called)  # No retry delay on permanent error

    def test_all_providers_fail_graceful_deterministic_fallback(self):
        """Verify all providers failing returns normalized failure and safe deterministic responses."""
        os.environ["LLM_PRIMARY_MODEL"] = "primary-model"
        os.environ["LLM_FALLBACK_MODELS"] = "fallback-model"
        os.environ["LLM_MAX_RETRIES"] = "0"

        server_err = MagicMock()
        server_err.status_code = 500
        server_err.headers = {}

        with patch("services.llm_service.LLMService.get_api_key", return_value="fake-api-key"):
            with patch("requests.post", return_value=server_err):
                # 1. execute_completion returns normalized exhausted error
                res = LLMService.execute_completion([{"role": "user", "content": "Test"}])
                self.assertFalse(res["success"])
                self.assertEqual(res["error_category"], "exhausted_fallbacks")

                # 2. ask_financial_assistant falls back gracefully without crashing
                ans = LLMService.ask_financial_assistant("Is Infosys good?")
                self.assertTrue(ans["success"])
                self.assertIn("Offline Mode", ans["answer"])

                # 3. generate_stock_explanation returns deterministic synthesis
                expl = LLMService.generate_stock_explanation(
                    "INFY.NS",
                    {"name": "Infosys", "price": 1800},
                    {"overall_score": 75, "signal": "BUY", "risk_label": "Low Risk", "factor_scores": {}}
                )
                self.assertIn("INFY.NS", expl)
                self.assertIn("BUY", expl)

                # 4. analyze_portfolio_ai returns deterministic portfolio synthesis
                summary = {
                    "has_holdings": True,
                    "total_invested": 100000,
                    "total_value": 110000,
                    "unrealized_pnl": 10000,
                    "unrealized_pnl_pct": 10.0,
                    "realized_pnl": 0,
                    "total_return_pct": 10.0,
                    "health_score": 80,
                    "health_label": "Healthy",
                    "holdings": [{"display_symbol": "TCS", "name": "Tata", "quantity": 10, "invested_value": 30000, "current_value": 35000, "unrealized_pnl_pct": 16.6, "allocation_pct": 31.8}],
                    "sector_allocation": [{"sector": "Technology", "percentage": 100, "value": 35000}]
                }
                port_ai = LLMService.analyze_portfolio_ai(summary)
                self.assertTrue(port_ai["success"])
                self.assertIn("portfolio", port_ai["summary"].lower())
                self.assertTrue(len(port_ai["strengths"]) > 0)
                self.assertTrue(len(port_ai["risks"]) > 0)

    def test_normalized_response_structure(self):
        """Verify execute_completion always returns the complete normalized schema."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Sample content"}}]
        }

        with patch("services.llm_service.LLMService.get_api_key", return_value="fake-api-key"):
            with patch("requests.post", return_value=mock_resp):
                res = LLMService.execute_completion([{"role": "user", "content": "Test"}])

                expected_keys = {
                    "success",
                    "content",
                    "model_used",
                    "provider",
                    "duration_ms",
                    "retries",
                    "attempts",
                    "fallback_used",
                    "error",
                    "error_category"
                }
                self.assertTrue(expected_keys.issubset(set(res.keys())))
                self.assertIsInstance(res["success"], bool)
                self.assertIsInstance(res["duration_ms"], float)
                self.assertIsInstance(res["retries"], int)
                self.assertIsInstance(res["attempts"], int)

    def test_retry_limit_enforced(self):
        """Verify retries strictly adhere to LLM_MAX_RETRIES count."""
        os.environ["LLM_PRIMARY_MODEL"] = "test-model"
        os.environ["LLM_FALLBACK_MODELS"] = ""
        os.environ["LLM_MAX_RETRIES"] = "2"

        server_err = MagicMock()
        server_err.status_code = 503
        server_err.headers = {}

        with patch("services.llm_service.LLMService.get_api_key", return_value="fake-api-key"):
            with patch("time.sleep"):
                with patch("requests.post", return_value=server_err) as mock_post:
                    res = LLMService.execute_completion([{"role": "user", "content": "Test"}])

                    self.assertFalse(res["success"])
                    # Initial attempt + 2 retries = 3 total attempts
                    self.assertEqual(mock_post.call_count, 3)
                    self.assertEqual(res["retries"], 2)
                    self.assertEqual(res["attempts"], 3)


if __name__ == "__main__":
    unittest.main()
