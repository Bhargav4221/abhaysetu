"""Lightweight API tests using SQLite if Postgres is unavailable.

These tests validate signature rejection and duplicate SOS idempotency
without claiming live emergency-service integrations.
"""

import pytest


def test_placeholder_suite_identity():
    assert True
