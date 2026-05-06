"""Shared pytest configuration for programgarden_finance tests."""

from __future__ import annotations


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "field_metadata: AI-chatbot-ready Field metadata coverage "
        "(InBlock / OutBlock / Real body) across every LS TR blocks.py.",
    )
