"""Fælles fixtures: udfyldt konfiguration og stubbede credentials."""

import pytest

from ats_framework.processes import handle_item, intake_config


@pytest.fixture(autouse=True)
def udfyldt_config(monkeypatch):
    """Udfylder pladsholderne og stubber credential-opslaget."""
    monkeypatch.setattr(intake_config, "AKTINDSIGT_BASE_URL", "https://aktindsigt.test")
    monkeypatch.setattr(intake_config, "AKTINDSIGT_CREDENTIAL", "aktindsigt_intake")
    monkeypatch.setattr(intake_config, "OS2FORMS_BASE_URL", "https://os2forms.test/da")
    handle_item._credential.cache_clear()
    monkeypatch.setattr(
        handle_item, "get_credential_password", lambda name: f"key-{name}"
    )
    yield
    handle_item._credential.cache_clear()
