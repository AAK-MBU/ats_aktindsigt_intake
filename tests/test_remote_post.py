"""Kroppen læses af aktindsigt, som Remote post-kroppen blev."""

import pytest

from ats_framework.processes.remote_post import Filblok, build_form_items, flatten
from tests.aktindsigt_reference import fuldmagt_bytes, parse_felter
from tests.testdata import (
    EGEN_ANMODNING,
    MUNDTLIG_ANMODNING,
    PAA_ANDRES_VEGNE,
    SMALL_PDF,
    UUID,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("tekst", [("f", "tekst")]),
        ("", [("f", "")]),
        (None, []),
        (True, [("f", "1")]),
        (False, [("f", "0")]),
        (42, [("f", "42")]),
        (["a", "b"], [("f[0]", "a"), ("f[1]", "b")]),
        ([], []),
        ({"name": "N", "email": "E"}, [("f[name]", "N"), ("f[email]", "E")]),
        ([{"x": "1"}], [("f[0][x]", "1")]),
    ],
)
def test_flatten_koder_som_http_build_query(value, expected):
    assert list(flatten("f", value)) == expected


def test_egen_anmodning_laeses_med_formularens_feltnavne():
    items = build_form_items(
        "aktindsigt_medarbejder_indgang_p", UUID, EGEN_ANMODNING, []
    )
    felter = parse_felter(items)

    assert felter["webform_id"] == "aktindsigt_medarbejder_indgang_p"
    assert felter["submission_uuid"] == UUID
    assert felter["navn_login"] == "Testperson Et"
    assert felter["cpr_nummer_medarbejder"] == "0000000000"
    assert felter["angiv_dit_tjenestenummer"] == "204815"
    assert felter["angiv_navn_paa_den_medarbejder_du_soeger_aktindsigt_i"] == ""
    assert felter["vaelg_undermapper"] == ["Sygdom og fravær", "Løn"]
    assert fuldmagt_bytes(felter, "_upload_fuldmagt") is None


def test_fuldmagt_sendes_som_remote_post_filblok():
    fil = Filblok(
        blok="_upload_fuldmagt",
        fil_id="506337",
        navn="fuldmagt.pdf",
        mime="application/pdf",
        indhold=SMALL_PDF,
    )
    items = build_form_items(
        "aktindsigt_medarbejder_indgang_p", UUID, PAA_ANDRES_VEGNE, [fil]
    )
    felter = parse_felter(items)

    assert fuldmagt_bytes(felter, "_upload_fuldmagt") == SMALL_PDF
    assert felter["_upload_fuldmagt"]["name"] == "fuldmagt.pdf"
    assert felter["_upload_fuldmagt"]["mime"] == "application/pdf"
    assert felter["_upload_fuldmagt"]["id"] == "506337"
    assert felter["virksomhedens_navn"] == "Advokatfirmaet A/S"
    assert felter["cvr_nummer"] == "00000000"


def test_attachments_sendes_ikke_som_felt():
    items = build_form_items(
        "aktindsigt_medarbejder_indgang_p", UUID, PAA_ANDRES_VEGNE, []
    )
    assert not any(navn.startswith("attachments") for navn, _ in items)


def test_mundtlig_anmodning_bevarer_sammensat_element_og_dato():
    items = build_form_items(
        "aktindsigt_indgang_personale", UUID, MUNDTLIG_ANMODNING, []
    )
    felter = parse_felter(items)

    assert felter["webform_id"] == "aktindsigt_indgang_personale"
    assert felter["dine_oplysninger_medarbejder"] == {
        "name": "Jurist Juristsen",
        "email": "jurist@example.invalid",
    }
    assert (
        felter["angiv_den_dato_hvor_medarbejderen_kontaktede_personalejuristerne"]
        == "2026-09-14"
    )
    assert felter["tjenestenummer_medarbejder"] == "12345"


def test_webform_id_og_uuid_vinder_over_felter_med_samme_navn():
    data = {**EGEN_ANMODNING, "webform_id": "forkert", "submission_uuid": "forkert"}
    items = build_form_items("aktindsigt_medarbejder_indgang_p", UUID, data, [])
    felter = parse_felter(items)

    assert felter["webform_id"] == "aktindsigt_medarbejder_indgang_p"
    assert felter["submission_uuid"] == UUID
    assert items[0] == ("webform_id", "aktindsigt_medarbejder_indgang_p")
    assert items[-1] == ("submission_uuid", UUID)
