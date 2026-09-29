"""Afsendelse af en indsendelse til aktindsigts intake.

Kalder ``POST {AKTINDSIGT_BASE_URL}/api/intake/sager`` som
``application/x-www-form-urlencoded`` med headeren ``X-API-Key``. Svaret er
``{"sagId": <int>}``: ``201`` for en ny sag, ``200`` når svarets uuid allerede
står på en sag. ``422`` betyder, at indsendelsen ikke kan omkodes; ``detail``
beskriver hvorfor.

Indsendelsens indhold (CPR, base64-filer) logges aldrig, og ``detail`` renses
for cifferfølger på 10, før den indgår i en besked.
"""

import logging
import re
from dataclasses import dataclass
from http import HTTPStatus

import requests

from ats_framework.processes import intake_config

logger = logging.getLogger(__name__)

API_KEY_HEADER = "X-API-Key"
INTAKE_PATH = "/api/intake/sager"

# 10 cifre med valgfri bindestreg efter de 6 første: CPR-formen.
_CPR_RE = re.compile(r"\d{6}-?\d{4}")


class AktindsigtAfvist(ValueError):
    """Aktindsigt svarede 422: indsendelsen kan ikke omkodes til en sag."""


class AktindsigtFejl(RuntimeError):
    """Aktindsigt kunne ikke spørges: login, serverfejl, timeout eller netværk."""


@dataclass(frozen=True)
class Modtaget:
    """Aktindsigts kvittering.

    Attributes:
        sag_id: Sagens id i portalen.
        ny: ``True`` ved en ny sag (201), ``False`` når svaret allerede var
            modtaget (200).
    """

    sag_id: int
    ny: bool


def rens(tekst: str) -> str:
    """Fjerner CPR-lignende cifferfølger fra en tekst.

    Args:
        tekst: Teksten, fx aktindsigts fejlbeskrivelse.

    Returns:
        Teksten med hver CPR-lignende følge erstattet af ``<cpr>``.
    """
    return _CPR_RE.sub("<cpr>", tekst)


def beskriv_detail(detail: object) -> str:
    """Gør aktindsigts ``detail`` til en kort, renset tekst.

    ``detail`` er enten en streng (ukendt webform, ugyldig fuldmagt, ugyldigt
    uuid) eller pydantics fejlliste. Fra fejllisten bruges kun ``loc`` og
    ``msg``: ``input`` kan bære den afviste værdi, fx et CPR.

    Args:
        detail: ``detail`` fra aktindsigts 422-svar.

    Returns:
        En renset tekst.
    """
    if isinstance(detail, list):
        dele = []
        for fejl in detail:
            if not isinstance(fejl, dict):
                continue
            loc = ".".join(str(x) for x in fejl.get("loc") or [])
            dele.append(f"{loc}: {fejl.get('msg', '')}".strip(": "))
        return rens("; ".join(dele) or "ukendt valideringsfejl")
    return rens(str(detail))


def send_sag(items: list[tuple[str, str]], api_key: str) -> Modtaget:
    """Sender indsendelsen til aktindsigt.

    Args:
        items: Felterne fra ``remote_post.build_form_items``.
        api_key: Aktindsigts intake-API-nøgle.

    Returns:
        Kvitteringen med sagens id.

    Raises:
        AktindsigtAfvist: Ved 422.
        AktindsigtFejl: Ved andre fejlkoder, netværksfejl, eller et svar uden
            ``sagId``.
    """
    url = f"{intake_config.AKTINDSIGT_BASE_URL.rstrip('/')}{INTAKE_PATH}"
    try:
        response = requests.post(
            url,
            data=items,
            headers={API_KEY_HEADER: api_key},
            timeout=intake_config.HTTP_TIMEOUT,
        )
    except requests.RequestException as e:
        raise AktindsigtFejl(
            f"Aktindsigt could not be reached: {type(e).__name__}"
        ) from e

    if response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY:
        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = "ingen detail i svaret"
        raise AktindsigtAfvist(beskriv_detail(detail))
    if response.status_code not in (HTTPStatus.OK, HTTPStatus.CREATED):
        raise AktindsigtFejl(f"Aktindsigt returned {response.status_code}")

    try:
        sag_id = int(response.json()["sagId"])
    except (ValueError, KeyError, TypeError) as e:
        raise AktindsigtFejl("Aktindsigt response had no sagId") from e
    return Modtaget(sag_id=sag_id, ny=response.status_code == HTTPStatus.CREATED)
