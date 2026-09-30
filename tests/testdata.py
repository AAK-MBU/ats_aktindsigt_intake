"""Fælles testdata: webform_rest-svar på de to aktindsigt-webforms.

Felterne er dem, aktindsigts egne intake-tests sender (``test_intake.py``),
i den form webform_rest leverer dem: lister som lister, sammensatte
elementer som dicts, en uploadet fil som id med metadata i ``linked`` og
genererede kvitteringer i ``attachments``. Alle CPR-numre er ``0000000000``.
"""

UUID = "3f2a8c1e-5b6d-4e7f-8a9b-0c1d2e3f4a5b"
FIL_URL = "https://os2forms.test/system/files/webform/aktindsigt/227894/fuldmagt%20underskrevet.pdf"
FIL_ID = "506487"

SMALL_PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"

EGEN_ANMODNING = {
    "navn_login": "Testperson Et",
    "cpr_nummer_medarbejder": "0000000000",
    "angiv_dit_tjenestenummer": "204815",
    "angiv_navn_paa_den_medarbejder_du_soeger_aktindsigt_i": "",
    "angiv_cpr_nummer_paa_den_medarbejder_du_soeger_aktindsigt_i": "",
    "angiv_tjenestenummer_paa_den_medarbejder_du_soeger_aktindsigt_i": "",
    # Radioknappen vises kun for en virksomhed; ved en egen anmodning er den tom.
    "ansoegning_om_aktindsigt": "",
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
    "upload_fuldmagt": FIL_ID,
    "test_cpr": "",
    # Den uploadede fil: værdien ovenfor er dens id, metadata står i linked.
    "linked": {
        "upload_fuldmagt": {
            FIL_ID: {
                "id": FIL_ID,
                "url": FIL_URL,
                "mime_type": "application/pdf",
                "size": 28327,
            }
        }
    },
    # Genererede kvitteringer; ikke formularens filer.
    "attachments": {
        "kvitteringsbrev_til_medarbejder": {
            "name": "Kvitteringsbrev til medarbejder",
            "type": "pdf",
            "url": "https://os2forms.test/kvittering-medarbejder.pdf",
        },
        "kvitteringsbrev_til_organisation_advokat": {
            "name": "Kvitteringsbrev faglig organisation/advokat",
            "type": "pdf",
            "url": "https://os2forms.test/kvittering-organisation.pdf",
        },
    },
}

MUNDTLIG_ANMODNING = {
    "dine_oplysninger_medarbejder": {
        "az": "az00000",
        "email": "jurist@example.invalid",
        "location": "",
        "magistrat": "",
        "name": "Jurist Juristsen",
        "organisations_funktion": "",
        "organisation_adresse": "",
        "organisation_enhed": "",
        "organisation_niveau_2": "",
        "phone": "",
        "search": "",
        "search_query": "",
        "search_user_id": "",
        "stillingsbetegnelse": "Personalejuridisk konsulent",
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
    "attachments": {
        "kvitteringsbrev_til_medarbejder": {
            "name": "Kvitteringsbrev til medarbejder",
            "type": "pdf",
            "url": "https://os2forms.test/kvittering-medarbejder.pdf",
        }
    },
}


def svar(data: dict, webform_id: str = "aktindsigt_medarbejder_indgang_p") -> dict:
    """Et webform_rest-svar med ``entity`` og ``data``."""
    return {
        "entity": {
            "serial": [{"value": 16}],
            "sid": [{"value": 227894}],
            "uuid": [{"value": UUID}],
            "webform_id": [
                {
                    "target_id": webform_id,
                    "target_type": "webform",
                    "url": f"/da/form/{webform_id.replace('_', '-')}",
                }
            ],
        },
        "data": data,
    }
