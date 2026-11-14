"""Test di struttura per gli esempi in examples/ (dashboard e automazioni)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def test_dashboard_yaml_struttura_valida():
    data = yaml.safe_load((EXAMPLES_DIR / "dashboard.yaml").read_text(encoding="utf-8"))
    assert data["title"] == "Hattrick"
    assert isinstance(data["views"], list) and len(data["views"]) >= 1
    for view in data["views"]:
        assert "title" in view
        assert isinstance(view["cards"], list) and view["cards"]
        for card in view["cards"]:
            assert "type" in card


def test_dashboard_riferimenti_sensor_esistono():
    """Ogni sensor.* nel dashboard deve corrispondere a un nome di sensor tradotto."""
    translations = json.loads(
        (
            Path(__file__).resolve().parent.parent
            / "custom_components/hattrick/translations/it.json"
        ).read_text(encoding="utf-8")
    )
    sensor_keys = set(translations["entity"]["sensor"].keys())
    raw = (EXAMPLES_DIR / "dashboard.yaml").read_text(encoding="utf-8")
    # ignora i commenti: possono contenere entity_id di esempio con suffisso numerico
    text = "\n".join(
        line for line in raw.splitlines() if not line.lstrip().startswith("#")
    )
    for match in re.findall(r"sensor\.([a-z0-9_]+)", text):
        # gli entity_id derivano dai nomi tradotti: ricostruisci lo slug dal nome
        found = any(
            re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") == match
            for name in (v["name"] for v in translations["entity"]["sensor"].values())
        )
        assert found, f"entity_id sensor.{match} non corrisponde a nessun sensor tradotto"
        assert sensor_keys  # sanity: la sezione sensor esiste


def test_automations_yaml_struttura_valida():
    data = yaml.safe_load((EXAMPLES_DIR / "automations.yaml").read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) >= 3
    for automation in data:
        assert automation["alias"]
        assert automation["trigger"]
        assert automation["action"]


def test_automations_usano_servizi_hattrick_esistenti():
    text = (EXAMPLES_DIR / "automations.yaml").read_text(encoding="utf-8")
    services_yaml = yaml.safe_load(
        (
            Path(__file__).resolve().parent.parent / "custom_components/hattrick/services.yaml"
        ).read_text(encoding="utf-8")
    )
    for match in re.findall(r"action: (hattrick\.[a-z_]+)", text):
        service = match.split(".", 1)[1]
        assert service in services_yaml, f"servizio {match} non presente in services.yaml"
