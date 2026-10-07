"""
tests/unit/test_config.py
=========================
Unit tests for the configuration management module.
"""

import pytest
from backend.core.config import Settings


class TestSettings:
    def test_defaults_are_set(self):
        # Create Settings WITHOUT loading .env so we test code-level defaults only
        s = Settings(_env_file=None)
        assert s.APP_ENV == "development"
        assert s.DATABASE_POOL_SIZE == 10
        assert s.ACTIVE_FAILURE_MODEL == "random_forest"

    def test_cors_origins_parsed_correctly(self):
        s = Settings(CORS_ORIGINS="http://localhost:5173,http://localhost:3000")
        origins = s.cors_origins_list
        assert "http://localhost:5173" in origins
        assert "http://localhost:3000" in origins
        assert len(origins) == 2

    def test_cors_single_origin(self):
        s = Settings(CORS_ORIGINS="http://localhost:5173")
        assert s.cors_origins_list == ["http://localhost:5173"]

    def test_is_production_false_in_development(self):
        s = Settings(APP_ENV="development")
        assert s.is_production is False

    def test_is_production_true_in_production(self):
        s = Settings(APP_ENV="production")
        assert s.is_production is True

    def test_anomaly_threshold_range(self):
        s = Settings(ANOMALY_THRESHOLD=0.7)
        assert s.ANOMALY_THRESHOLD == 0.7

    def test_risk_alert_threshold(self):
        s = Settings(RISK_SCORE_ALERT_THRESHOLD=80.0)
        assert s.RISK_SCORE_ALERT_THRESHOLD == 80.0
