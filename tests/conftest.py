"""Fixture condivise dei test dell'integrazione Hattrick."""

import sys
from pathlib import Path

import pytest

# Rende importabile il package custom_components senza installare HA.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Carica le custom integration nei test (standard PHACC)."""
    yield
