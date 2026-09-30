"""Forløbet og udfaldene for ét workitem."""

import pytest
from mbu_rpa_core.exceptions import BusinessError, ProcessError

from ats_framework.helpers import aktindsigt, os2forms
from ats_framework.processes import handle_item
from tests.aktindsigt_reference import fuldmagt_bytes, parse_felter
from tests.testdata import (
    EGEN_ANMODNING,
    FIL_ID,
    FIL_URL,
    MUNDTLIG_ANMODNING,
    PAA_ANDRES_VEGNE,
    SMALL_PDF,
    UUID,
    svar,
)

MEDARBEJDER = "aktindsigt_medarbejder_indgang_p"


@pytest.fixture
def kald(monkeypatch):
    """Stubber OS2Forms og aktindsigt og registrerer kaldene."""
    log = {"submission": [], "attachment": [], "sendt": []}
    state = {
        "svar": svar(EGEN_ANMODNING),
        "fil": os2forms.Fil(indhold=SMALL_PDF, content_type="application/pdf"),
        "kvittering": aktindsigt.Modtaget(sag_id=7, ny=True),
    }

    def fetch_submission(webform_id, uuid, api_key):
        log["submission"].append((webform_id, uuid, api_key))
        if isinstance(state["svar"], Exception):
            raise state["svar"]
        return state["svar"]

    def fetch_attachment(url, api_key):
        log["attachment"].append((url, api_key))
        if isinstance(state["fil"], Exception):
            raise state["fil"]
        return state["fil"]

    def send_sag(items, api_key):
        log["sendt"].append((items, api_key))
        if isinstance(state["kvittering"], Exception):
            raise state["kvittering"]
        return state["kvittering"]

    monkeypatch.setattr(os2forms, "fetch_submission", fetch_submission)
    monkeypatch.setattr(os2forms, "fetch_attachment", fetch_attachment)
    monkeypatch.setattr(aktindsigt, "send_sag", send_sag)
    return state, log


def test_ny_sag_giver_besked_med_sag_id(kald):
    state, log = kald

    besked = handle_item.handle_item({"webformId": MEDARBEJDER, "serial": 12}, UUID)

    assert besked == "Sag 7 oprettet i aktindsigt"
    assert log["submission"] == [(MEDARBEJDER, UUID, "key-os2_api")]
    items, api_key = log["sendt"][0]
    assert api_key == "key-aktindsigt_intake"
    felter = parse_felter(items)
    assert felter["submission_uuid"] == UUID
    assert felter["webform_id"] == MEDARBEJDER
    assert log["attachment"] == []


def test_allerede_modtaget_giver_egen_besked(kald):
    state, _ = kald
    state["kvittering"] = aktindsigt.Modtaget(sag_id=7, ny=False)

    besked = handle_item.handle_item({"webformId": MEDARBEJDER}, UUID)

    assert besked == "Allerede modtaget i aktindsigt som sag 7"


def test_fuldmagt_hentes_og_sendes_base64(kald):
    state, log = kald
    state["svar"] = svar(PAA_ANDRES_VEGNE)

    handle_item.handle_item({"webformId": MEDARBEJDER}, UUID)

    assert log["attachment"] == [(FIL_URL, "key-os2_api")]
    felter = parse_felter(log["sendt"][0][0])
    assert fuldmagt_bytes(felter, "_upload_fuldmagt") == SMALL_PDF
    assert felter["_upload_fuldmagt"]["mime"] == "application/pdf"
    assert felter["_upload_fuldmagt"]["id"] == FIL_ID


def test_filnavnet_tages_af_url_ens_sidste_led(kald):
    state, log = kald
    state["svar"] = svar(PAA_ANDRES_VEGNE)

    handle_item.handle_item({"webformId": MEDARBEJDER}, UUID)

    felter = parse_felter(log["sendt"][0][0])
    assert felter["_upload_fuldmagt"]["name"] == "fuldmagt underskrevet.pdf"


def test_kvitteringer_og_linked_hentes_og_sendes_ikke(kald):
    state, log = kald
    state["svar"] = svar(PAA_ANDRES_VEGNE)

    handle_item.handle_item({"webformId": MEDARBEJDER}, UUID)

    # Kun den uploadede fil hentes, ikke OS2Forms' genererede kvitteringer.
    assert log["attachment"] == [(FIL_URL, "key-os2_api")]
    navne = [navn for navn, _ in log["sendt"][0][0]]
    assert not any(n.startswith(("attachments", "linked")) for n in navne)


def test_mime_udledes_af_endelsen_naar_mime_type_og_header_mangler(kald):
    state, log = kald
    uden_mime = {FIL_ID: {"id": FIL_ID, "url": FIL_URL, "mime_type": ""}}
    state["svar"] = svar({**PAA_ANDRES_VEGNE, "linked": {"upload_fuldmagt": uden_mime}})
    state["fil"] = os2forms.Fil(indhold=SMALL_PDF, content_type="")

    handle_item.handle_item({"webformId": MEDARBEJDER}, UUID)

    felter = parse_felter(log["sendt"][0][0])
    assert felter["_upload_fuldmagt"]["mime"] == "application/pdf"


def test_personale_indgang_har_ingen_filfelter(kald):
    state, log = kald
    state["svar"] = svar(MUNDTLIG_ANMODNING, "aktindsigt_indgang_personale")

    handle_item.handle_item({"webformId": "aktindsigt_indgang_personale"}, UUID)

    felter = parse_felter(log["sendt"][0][0])
    assert felter["webform_id"] == "aktindsigt_indgang_personale"
    assert log["attachment"] == []


def test_webform_id_laeses_af_raa_payload(kald):
    _, log = kald

    handle_item.handle_item(svar(EGEN_ANMODNING), UUID)

    assert log["submission"][0][0] == MEDARBEJDER


@pytest.mark.parametrize(
    ("data", "reference", "fejltekst"),
    [
        ({"webformId": MEDARBEJDER}, "", "ingen reference"),
        ({"serial": 1}, UUID, "ingen webform"),
        ({"webformId": "en_anden_formular"}, UUID, "sendes ikke til aktindsigt"),
    ],
)
def test_ugyldigt_item_er_forretningsfejl(kald, data, reference, fejltekst):
    _, log = kald

    with pytest.raises(BusinessError, match=fejltekst):
        handle_item.handle_item(data, reference)
    assert log["submission"] == []


def test_svar_der_ikke_findes_er_forretningsfejl(kald):
    state, log = kald
    state["svar"] = os2forms.OS2FormsNotFound("404")

    with pytest.raises(BusinessError, match="findes ikke i OS2Forms"):
        handle_item.handle_item({"webformId": MEDARBEJDER}, UUID)
    assert log["sendt"] == []


def test_os2forms_utilgaengelig_er_procesfejl(kald):
    state, _ = kald
    state["svar"] = os2forms.OS2FormsError("OS2Forms returned 503")

    with pytest.raises(ProcessError):
        handle_item.handle_item({"webformId": MEDARBEJDER}, UUID)


def test_svar_uden_formulardata_er_forretningsfejl(kald):
    state, _ = kald
    state["svar"] = {"entity": {}}

    with pytest.raises(BusinessError, match="ingen formulardata"):
        handle_item.handle_item({"webformId": MEDARBEJDER}, UUID)


def test_udfyldt_filfelt_uden_link_er_forretningsfejl(kald):
    state, log = kald
    state["svar"] = svar({**PAA_ANDRES_VEGNE, "linked": {}})

    with pytest.raises(BusinessError, match="intet link"):
        handle_item.handle_item({"webformId": MEDARBEJDER}, UUID)
    assert log["sendt"] == []


def test_manglende_fil_i_os2forms_er_forretningsfejl(kald):
    state, log = kald
    state["svar"] = svar(PAA_ANDRES_VEGNE)
    state["fil"] = os2forms.OS2FormsNotFound("404")

    with pytest.raises(BusinessError, match="uploadede fil"):
        handle_item.handle_item({"webformId": MEDARBEJDER}, UUID)
    assert log["sendt"] == []


def test_fil_der_ikke_kan_hentes_er_procesfejl(kald):
    state, _ = kald
    state["svar"] = svar(PAA_ANDRES_VEGNE)
    state["fil"] = os2forms.OS2FormsError("OS2Forms returned 500")

    with pytest.raises(ProcessError):
        handle_item.handle_item({"webformId": MEDARBEJDER}, UUID)


def test_afvisning_fra_aktindsigt_er_forretningsfejl(kald):
    state, _ = kald
    state["kvittering"] = aktindsigt.AktindsigtAfvist("aktperson_cpr: ugyldigt")

    with pytest.raises(BusinessError, match="422.*aktperson_cpr"):
        handle_item.handle_item({"webformId": MEDARBEJDER}, UUID)


def test_aktindsigt_utilgaengelig_er_procesfejl(kald):
    state, _ = kald
    state["kvittering"] = aktindsigt.AktindsigtFejl("Aktindsigt returned 503")

    with pytest.raises(ProcessError):
        handle_item.handle_item({"webformId": MEDARBEJDER}, UUID)


@pytest.mark.usefixtures("kald")
def test_credentials_hentes_en_gang_pr_koersel(monkeypatch):
    kaldte = []
    monkeypatch.setattr(
        handle_item,
        "get_credential_password",
        lambda name: kaldte.append(name) or f"key-{name}",
    )

    handle_item.handle_item({"webformId": MEDARBEJDER}, UUID)
    handle_item.handle_item({"webformId": MEDARBEJDER}, UUID)

    assert sorted(kaldte) == ["aktindsigt_intake", "os2_api"]
