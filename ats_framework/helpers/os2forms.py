"""Hentning af formularsvar og vedhæftninger fra OS2Forms.

Kalder OS2Forms' REST-API (``os2forms_rest_api``) med headeren ``api-key``:

- ``GET {base}/webform_rest/{webform_id}/submission/{uuid}`` giver svaret som
  ``{"entity": {...}, "data": {...}}``. ``data`` er formularens felter med
  elementernes maskinnavne som nøgler; vedhæftninger står under
  ``data["attachments"]`` som ``{"<element>": {"name", "type", "url"}}``.
- ``GET <vedhæftningens url>`` med samme header giver filens bytes.

HTTP-fejl oversættes til ``OS2FormsNotFound`` (404: svaret eller filen findes
ikke) og ``OS2FormsError`` (alt andet: login, serverfejl, netværk).
Svarets indhold logges aldrig.
"""

import logging
from dataclasses import dataclass
from http import HTTPStatus

import requests

from ats_framework.processes import intake_config

logger = logging.getLogger(__name__)

API_KEY_HEADER = "api-key"


class OS2FormsError(RuntimeError):
    """OS2Forms kunne ikke spørges: login, serverfejl, timeout eller netværk."""


class OS2FormsNotFound(LookupError):
    """OS2Forms svarede 404: svaret eller vedhæftningen findes ikke."""


@dataclass(frozen=True)
class Fil:
    """En hentet vedhæftning.

    Attributes:
        indhold: Filens bytes.
        content_type: ``Content-Type`` fra OS2Forms' svar uden parametre,
            eller ``""`` hvis headeren mangler.
    """

    indhold: bytes
    content_type: str


def _get(url: str, api_key: str) -> requests.Response:
    """Kalder OS2Forms og oversætter fejl.

    Args:
        url: Den fulde URL.
        api_key: OS2Forms' api-key.

    Returns:
        Svaret ved statuskode under 400.

    Raises:
        OS2FormsNotFound: Ved 404.
        OS2FormsError: Ved andre fejlkoder og ved netværksfejl.
    """
    try:
        response = requests.get(
            url,
            headers={API_KEY_HEADER: api_key},
            timeout=intake_config.HTTP_TIMEOUT,
        )
    except requests.RequestException as e:
        raise OS2FormsError(f"OS2Forms could not be reached: {type(e).__name__}") from e
    if response.status_code == HTTPStatus.NOT_FOUND:
        raise OS2FormsNotFound(f"OS2Forms returned 404 for {url}")
    if response.status_code >= HTTPStatus.BAD_REQUEST:
        raise OS2FormsError(f"OS2Forms returned {response.status_code} for {url}")
    return response


def fetch_submission(webform_id: str, uuid: str, api_key: str) -> dict:
    """Henter ét svar på en webform.

    Args:
        webform_id: Webformens maskinnavn.
        uuid: Svarets uuid.
        api_key: OS2Forms' api-key.

    Returns:
        Svaret som ``{"entity": ..., "data": ...}``.

    Raises:
        OS2FormsNotFound: Hvis svaret ikke findes.
        OS2FormsError: Hvis OS2Forms ikke kunne spørges, eller svaret ikke er
            et JSON-objekt.
    """
    url = (
        f"{intake_config.OS2FORMS_BASE_URL.rstrip('/')}"
        f"/webform_rest/{webform_id}/submission/{uuid}"
    )
    response = _get(url, api_key)
    try:
        payload = response.json()
    except ValueError as e:
        raise OS2FormsError(f"OS2Forms returned non-JSON for submission {uuid}") from e
    if not isinstance(payload, dict):
        raise OS2FormsError(f"OS2Forms submission {uuid} was not a JSON object")
    logger.info("Fetched submission %s from %s", uuid, webform_id)
    return payload


def fetch_attachment(url: str, api_key: str) -> Fil:
    """Henter en vedhæftning.

    Args:
        url: Vedhæftningens URL fra ``data["attachments"]``.
        api_key: OS2Forms' api-key.

    Returns:
        Filens bytes og content-type.

    Raises:
        OS2FormsNotFound: Hvis filen ikke findes.
        OS2FormsError: Hvis OS2Forms ikke kunne spørges.
    """
    response = _get(url, api_key)
    content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip()
    logger.info("Fetched attachment (%d bytes)", len(response.content))
    return Fil(indhold=response.content, content_type=content_type)
