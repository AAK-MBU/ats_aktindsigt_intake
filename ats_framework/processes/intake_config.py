"""Konfiguration af intake-processen: OS2Forms, aktindsigt og webforms.

Værdier med præfikset ``UDFYLDES_`` er pladsholdere. ``validate_config``
afviser dem, så en kørsel fejler højlydt, indtil de er udfyldt.
"""

from dataclasses import dataclass, field

PLACEHOLDER_PREFIX = "UDFYLDES_"

PROCESS_NAME = "ats_aktindsigt_intake"

# ----------------------
# OS2Forms
# ----------------------
OS2FORMS_BASE_URL = "https://selvbetjening.aarhuskommune.dk/da"
# Credential i rpa.Credentials, hvis password er OS2Forms' api-key.
OS2FORMS_CREDENTIAL = "os2_api"

# ----------------------
# Aktindsigt
# ----------------------
# Portalens backend, fx https://<vært>. Stien /api/intake/sager lægges til.
AKTINDSIGT_BASE_URL = "UDFYLDES_aktindsigt_base_url"
# Credential i rpa.Credentials, hvis password er aktindsigts intake-API-nøgle
# (sendes i headeren X-API-Key).
AKTINDSIGT_CREDENTIAL = "UDFYLDES_aktindsigt_credential"

# Timeout i sekunder pr. HTTP-kald.
HTTP_TIMEOUT = 60


@dataclass(frozen=True)
class WebformConfig:
    """Hvordan et svar på en webform sendes til aktindsigt.

    Attributes:
        filfelter: OS2Forms-elementets maskinnavn mappet til navnet på den
            filblok, aktindsigt læser filen i. Remote post sendte en fil som
            blokken ``_<element>[id|name|mime|data]``; aktindsigt læser
            fuldmagten i ``_upload_fuldmagt``.
    """

    filfelter: dict[str, str] = field(default_factory=dict)


# webform_id → konfiguration. Kun disse webforms behandles; et svar på en
# anden webform afvises som forretningsfejl.
#
# Elementnavnet ``upload_fuldmagt`` er udledt af Remote post-blokken
# ``_upload_fuldmagt`` (Remote post navngiver filblokken ``_`` + elementets
# maskinnavn) og er ikke verificeret mod webformens konfiguration i OS2Forms.
WEBFORMS: dict[str, WebformConfig] = {
    "aktindsigt_medarbejder_indgang_p": WebformConfig(
        filfelter={"upload_fuldmagt": "_upload_fuldmagt"},
    ),
    "aktindsigt_indgang_personale": WebformConfig(),
}


def validate_config() -> None:
    """Afviser konfiguration, der stadig indeholder pladsholdere.

    Raises:
        ValueError: Hvis en URL eller et credential-navn er en pladsholder,
            eller ingen webforms er konfigureret.
    """
    values = [
        OS2FORMS_BASE_URL,
        OS2FORMS_CREDENTIAL,
        AKTINDSIGT_BASE_URL,
        AKTINDSIGT_CREDENTIAL,
    ]
    placeholders = [v for v in values if v.startswith(PLACEHOLDER_PREFIX)]
    if placeholders:
        raise ValueError(
            f"intake_config contains unfilled placeholders: {placeholders}"
        )
    if not WEBFORMS:
        raise ValueError("intake_config.WEBFORMS is empty")
