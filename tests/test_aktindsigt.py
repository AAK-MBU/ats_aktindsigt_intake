"""Kaldet til aktindsigts intake og tolkningen af svaret."""

import pytest
import requests

from ats_framework.helpers import aktindsigt


class _Svar:
    def __init__(self, status_code, body=None, json_fejl=False):
        self.status_code = status_code
        self._body = body
        self._json_fejl = json_fejl

    def json(self):
        if self._json_fejl:
            raise ValueError("no json")
        return self._body


@pytest.fixture
def post(monkeypatch):
    """Stubber requests.post og registrerer kaldet."""
    kald = {}
    svar = {"value": _Svar(201, {"sagId": 7})}

    def fake_post(url, data, headers, timeout):
        kald.update(url=url, data=data, headers=headers, timeout=timeout)
        if isinstance(svar["value"], Exception):
            raise svar["value"]
        return svar["value"]

    monkeypatch.setattr(aktindsigt.requests, "post", fake_post)
    return kald, svar


def test_ny_sag(post):
    kald, _ = post

    modtaget = aktindsigt.send_sag([("webform_id", "x")], "hemmelig")

    assert modtaget == aktindsigt.Modtaget(sag_id=7, ny=True)
    assert kald["url"] == "https://aktindsigt.test/api/intake/sager"
    assert kald["headers"] == {"X-API-Key": "hemmelig"}
    assert kald["data"] == [("webform_id", "x")]


def test_allerede_modtaget(post):
    _, svar = post
    svar["value"] = _Svar(200, {"sagId": 7})

    assert aktindsigt.send_sag([], "k") == aktindsigt.Modtaget(sag_id=7, ny=False)


def test_422_med_valideringsliste_udelader_input(post):
    _, svar = post
    svar["value"] = _Svar(
        422,
        {
            "detail": [
                {
                    "loc": ["aktperson_cpr"],
                    "msg": "CPR skal være 10 cifre",
                    "input": "0101901234",
                }
            ]
        },
    )

    with pytest.raises(aktindsigt.AktindsigtAfvist) as info:
        aktindsigt.send_sag([], "k")
    assert str(info.value) == "aktperson_cpr: CPR skal være 10 cifre"
    assert "0101901234" not in str(info.value)


def test_422_med_tekst_renses_for_cpr(post):
    _, svar = post
    svar["value"] = _Svar(422, {"detail": "ugyldigt CPR 010190-1234 i feltet"})

    with pytest.raises(aktindsigt.AktindsigtAfvist, match="<cpr>") as info:
        aktindsigt.send_sag([], "k")
    assert "1234" not in str(info.value)


def test_422_uden_json(post):
    _, svar = post
    svar["value"] = _Svar(422, json_fejl=True)

    with pytest.raises(aktindsigt.AktindsigtAfvist, match="ingen detail"):
        aktindsigt.send_sag([], "k")


@pytest.mark.parametrize("status", [401, 403, 404, 500, 503])
def test_andre_statuskoder_er_fejl(post, status):
    _, svar = post
    svar["value"] = _Svar(status, {"detail": "x"})

    with pytest.raises(aktindsigt.AktindsigtFejl, match=str(status)):
        aktindsigt.send_sag([], "k")


def test_netvaerksfejl(post):
    _, svar = post
    svar["value"] = requests.Timeout("timeout")

    with pytest.raises(aktindsigt.AktindsigtFejl, match="Timeout"):
        aktindsigt.send_sag([], "k")


def test_svar_uden_sag_id(post):
    _, svar = post
    svar["value"] = _Svar(201, {})

    with pytest.raises(aktindsigt.AktindsigtFejl, match="sagId"):
        aktindsigt.send_sag([], "k")


def test_rens_lader_andre_tal_staa():
    assert aktindsigt.rens("tjenestenummer 12345, CPR 0101901234") == (
        "tjenestenummer 12345, CPR <cpr>"
    )
