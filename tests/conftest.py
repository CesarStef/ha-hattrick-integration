"""Fixture condivise dei test dell'integrazione Hattrick."""

import sys
from pathlib import Path

# Rende importabile il package custom_components senza installare HA.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
