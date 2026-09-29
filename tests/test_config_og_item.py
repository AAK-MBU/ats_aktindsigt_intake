"""Konfigurationsvalidering og udpakning af workitems."""

from types import SimpleNamespace

import pytest

from ats_framework.helpers.ats_functions import get_item_info
from ats_framework.processes import intake_config


def test_udfyldt_config_godkendes():
    intake_config.validate_config()


@pytest.mark.parametrize("navn", ["AKTINDSIGT_BASE_URL", "AKTINDSIGT_CREDENTIAL"])
def test_pladsholder_afvises(monkeypatch, navn):
    monkeypatch.setattr(intake_config, navn, "UDFYLDES_noget")

    with pytest.raises(ValueError, match="UDFYLDES_noget"):
        intake_config.validate_config()


def test_standardkonfigurationen_har_pladsholdere(monkeypatch):
    monkeypatch.undo()

    with pytest.raises(ValueError, match="UDFYLDES_"):
        intake_config.validate_config()


def test_ingen_webforms_afvises(monkeypatch):
    monkeypatch.setattr(intake_config, "WEBFORMS", {})

    with pytest.raises(ValueError, match="WEBFORMS"):
        intake_config.validate_config()


def test_kun_de_to_aktindsigt_webforms():
    assert set(intake_config.WEBFORMS) == {
        "aktindsigt_medarbejder_indgang_p",
        "aktindsigt_indgang_personale",
    }


def test_get_item_info_giver_payload_og_reference():
    item = SimpleNamespace(data={"webformId": "x"}, reference="uuid-1")
    assert get_item_info(item) == ({"webformId": "x"}, "uuid-1")


def test_get_item_info_uden_data():
    item = SimpleNamespace(data=None, reference=None)
    assert get_item_info(item) == ({}, "")
