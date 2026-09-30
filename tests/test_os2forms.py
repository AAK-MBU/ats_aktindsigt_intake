"""Hentning af svar og vedhæftninger fra OS2Forms."""

import pytest
import requests

from ats_framework.helpers import os2forms


class _Svar:
    def __init__(self, status_code, body=None, content=b"", headers=None):
        self.status_code = status_code
        self._body = body
        self.content = content
        self.headers = headers or {}

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


@pytest.fixture
def get(monkeypatch):
    """Stubber requests.get og registrerer kaldene."""
    kald = []
    svar = {"value": _Svar(200, {"entity": {}, "data": {}})}

    def fake_get(url, headers, timeout):
        kald.append((url, headers, timeout))
        if isinstance(svar["value"], Exception):
            raise svar["value"]
        return svar["value"]

    monkeypatch.setattr(os2forms.requests, "get", fake_get)
    return kald, svar


def test_fetch_submission_kalder_webform_rest(get):
    kald, _ = get

    payload = os2forms.fetch_submission("formular", "uuid-1", "nøgle")

    assert payload == {"entity": {}, "data": {}}
    url, headers, _ = kald[0]
    assert url == "https://os2forms.test/da/webform_rest/formular/submission/uuid-1"
    assert headers == {"api-key": "nøgle"}


def test_404_er_ikke_fundet(get):
    _, svar = get
    svar["value"] = _Svar(404)

    with pytest.raises(os2forms.OS2FormsNotFound):
        os2forms.fetch_submission("formular", "uuid-1", "k")


@pytest.mark.parametrize("status", [401, 403, 500, 503])
def test_andre_fejlkoder_er_fejl(get, status):
    _, svar = get
    svar["value"] = _Svar(status)

    with pytest.raises(os2forms.OS2FormsError, match=str(status)):
        os2forms.fetch_submission("formular", "uuid-1", "k")


def test_netvaerksfejl(get):
    _, svar = get
    svar["value"] = requests.ConnectionError("nede")

    with pytest.raises(os2forms.OS2FormsError, match="ConnectionError"):
        os2forms.fetch_submission("formular", "uuid-1", "k")


@pytest.mark.parametrize("body", [ValueError("no json"), ["ikke", "et", "objekt"]])
def test_svar_der_ikke_er_et_objekt(get, body):
    _, svar = get
    svar["value"] = _Svar(200, body)

    with pytest.raises(os2forms.OS2FormsError):
        os2forms.fetch_submission("formular", "uuid-1", "k")


def test_fetch_attachment_giver_bytes_og_content_type(get):
    kald, svar = get
    svar["value"] = _Svar(
        200,
        content=b"%PDF",
        headers={"Content-Type": "application/pdf; charset=binary"},
    )

    fil = os2forms.fetch_attachment("https://os2forms.test/fil.pdf", "nøgle")

    assert fil == os2forms.Fil(indhold=b"%PDF", content_type="application/pdf")
    assert kald[0][0] == "https://os2forms.test/fil.pdf"
    assert kald[0][1] == {"api-key": "nøgle"}
