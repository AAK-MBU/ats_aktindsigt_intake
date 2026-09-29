"""Fælles testdata: webform_rest-svar på de to aktindsigt-webforms.

Felterne er dem, aktindsigts egne intake-tests sender (``test_intake.py``),
i den form webform_rest leverer dem: lister som lister og sammensatte
elementer som dicts. Alle CPR-numre er ``0000000000``.
"""

UUID = "3f2a8c1e-5b6d-4e7f-8a9b-0c1d2e3f4a5b"
FIL_URL = "https://os2forms.test/system/files/webform/fuldmagt.pdf"

SMALL_PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"

EGEN_ANMODNING = {
    "navn_login": "Testperson Et",
    "cpr_nummer_medarbejder": "0000000000",
    "angiv_dit_tjenestenummer": "204815",
    "angiv_navn_paa_den_medarbejder_du_soeger_aktindsigt_i": "",
    "angiv_cpr_nummer_paa_den_medarbejder_du_soeger_aktindsigt_i": "",
    "angiv_tjenestenummer_paa_den_medarbejder_du_soeger_aktindsigt_i": "",
    "ansoegning_om_aktindsigt": "Jeg søger aktindsigt i egen personalemappe",
    "soeger_borgeren_indsigt_i_hele_eller_dele_af_personalesagen": (
        "Aktindsigt i dele af personalemappen"
    ),
    "vaelg_undermapper": ["Sygdom og fravær", "Løn"],
    "upload_fuldmagt": "",
}

PAA_ANDRES_VEGNE = {
    "navn_login": "Indsender Indsendersen",
    "virksomhedens_navn": "Advokatfirmaet A/S",
    "cvr_nummer": "00000000",
    "ansoegning_om_aktindsigt": "Anden repræsentant med fuldmagt",
    "angiv_navn_paa_den_medarbejder_du_soeger_aktindsigt_i": "Test Testesen",
    "angiv_cpr_nummer_paa_den_medarbejder_du_soeger_aktindsigt_i": "0000000000",
    "angiv_tjenestenummer_paa_den_medarbejder_du_soeger_aktindsigt_i": "12345",
    "soeger_borgeren_indsigt_i_hele_eller_dele_af_personalesagen": (
        "Aktindsigt i dele af personalemappen"
    ),
    "vaelg_undermapper": ["Sygdom og fravær"],
    "upload_fuldmagt": "506337",
    "attachments": {
        "upload_fuldmagt": {"name": "fuldmagt.pdf", "type": "pdf", "url": FIL_URL}
    },
}

MUNDTLIG_ANMODNING = {
    "dine_oplysninger_medarbejder": {
        "name": "Jurist Juristsen",
        "email": "jurist@example.invalid",
    },
    "navn_medarbejder": "Test Testesen",
    "cpr_nummer_medarbejder": "0000000000",
    "tjenestenummer_medarbejder": "12345",
    "angiv_den_dato_hvor_medarbejderen_kontaktede_personalejuristerne": "2026-09-14",
    "soeger_borgeren_indsigt_i_hele_eller_dele_af_personalesagen": (
        "Aktindsigt i dele af personalemappen"
    ),
    "vaelg_undermapper": ["Sygdom og fravær"],
    "ekstra_oplysninger": "Ringede på teamtelefonen.",
}


def svar(data: dict, webform_id: str = "aktindsigt_medarbejder_indgang_p") -> dict:
    """Et webform_rest-svar med ``entity`` og ``data``."""
    return {
        "entity": {
            "uuid": [{"value": UUID}],
            "webform_id": [{"target_id": webform_id}],
        },
        "data": data,
    }
