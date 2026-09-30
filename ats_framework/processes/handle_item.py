"""Behandler ét workitem: henter svaret i OS2Forms og sender det til aktindsigt.

Forløbet pr. item:

1. Webformens id læses af itemets data, og kun webforms i
   ``intake_config.WEBFORMS`` behandles.
2. Svaret hentes friskt fra OS2Forms ud fra itemets reference (svarets uuid).
3. Webformens filfelter hentes via deres links i ``data["linked"]``.
4. Indsendelsen bygges som Remote post-formen og sendes til aktindsigt.

Udfald:

- Aktindsigt svarer 201 eller 200: itemet er færdigt, og beskeden bærer
  sagens id.
- Forretningsfejl (``BusinessError``), som en medarbejder skal se på: ukendt
  eller manglende webform, svaret eller en vedhæftning findes ikke i OS2Forms,
  eller aktindsigt afviser indsendelsen (422).
- Procesfejl (``ProcessError``): OS2Forms eller aktindsigt kunne ikke spørges.

Beskeder og logs indeholder aldrig formularens indhold.
"""

import logging
import mimetypes
from functools import cache
from urllib.parse import unquote, urlsplit

from mbu_rpa_core.exceptions import BusinessError, ProcessError

from ats_framework.helpers import aktindsigt, os2forms
from ats_framework.helpers.rpa_db import get_credential_password
from ats_framework.processes import intake_config, remote_post

logger = logging.getLogger(__name__)


@cache
def _credential(name: str) -> str:
    """Henter en credentials password én gang pr. kørsel."""
    return get_credential_password(name)


def webform_id_fra_data(data: dict) -> str | None:
    """Læser webformens id ud af itemets data.

    Polling-servicen kan levere en payload med kun referencer
    (``{"webformId", "serial"}``) eller hele webform_rest-svaret, hvor id'et
    står i ``entity.webform_id[0].target_id``.

    Args:
        data: Itemets data.

    Returns:
        Webformens maskinnavn, eller ``None`` hvis det ikke findes.
    """
    for key in ("webformId", "webform_id"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    entity = data.get("entity")
    felt = entity.get("webform_id") if isinstance(entity, dict) else None
    if isinstance(felt, list) and felt and isinstance(felt[0], dict):
        value = felt[0].get("target_id") or felt[0].get("value")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _foerste(value: object) -> object:
    """Første element af en liste, ellers værdien selv."""
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _mime(fil_info: dict, navn: str, content_type: str) -> str:
    """Afgør en uploadet fils mime-type.

    Args:
        fil_info: Filens post fra ``data["linked"][<element>][<fil-id>]``.
        navn: Filens navn; endelsen bruges, når intet andet siger noget.
        content_type: ``Content-Type`` fra hentningen af filen.

    Returns:
        En mime-type. ``application/octet-stream`` hvis intet kan udledes.
    """
    mime = str(fil_info.get("mime_type") or "").strip()
    if "/" in mime:
        return mime
    if "/" in content_type:
        return content_type
    guessed, _ = mimetypes.guess_type(navn)
    return guessed or "application/octet-stream"


def _filnavn(url: str, element: str) -> str:
    """Filens navn, taget af URL'ens sidste led.

    ``data["linked"]`` har intet filnavn, men OS2Forms gemmer filen under
    dens oprindelige navn, som derfor står sidst i URL'en.

    Args:
        url: Filens URL.
        element: Filelementets maskinnavn; bruges, når URL'en intet navn har.

    Returns:
        Filnavnet, eller ``<element>.pdf``.
    """
    sidste = unquote(urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1])
    return sidste or f"{element}.pdf"


def hent_filblokke(
    data: dict,
    config: intake_config.WebformConfig,
    api_key: str,
) -> list[remote_post.Filblok]:
    """Henter webformens uploadede filer fra OS2Forms.

    Et filelements værdi i ``data`` er filens id. Filens URL og mime-type står
    i ``data["linked"][<element>][<fil-id>]``. ``data["attachments"]`` er de
    PDF'er, OS2Forms selv genererer (kvitteringer), og bruges ikke. Et
    filfelt uden værdi er en formular uden fil og giver ingen blok.

    Args:
        data: ``data`` fra webform_rest-svaret.
        config: Webformens konfiguration.
        api_key: OS2Forms' api-key.

    Returns:
        Én filblok pr. udfyldt filfelt.

    Raises:
        BusinessError: Hvis et udfyldt filfelt ikke har et link i
            ``data["linked"]``, eller filen ikke findes i OS2Forms.
        ProcessError: Hvis OS2Forms ikke kunne spørges.
    """
    linked = data.get(remote_post.LINKED_KEY)
    if not isinstance(linked, dict):
        linked = {}

    blokke = []
    for element, blok in config.filfelter.items():
        fil_id = _foerste(data.get(element))
        if fil_id in (None, ""):
            continue
        fil_id = str(fil_id)

        filer = linked.get(element)
        fil_info = filer.get(fil_id) if isinstance(filer, dict) else None
        url = fil_info.get("url") if isinstance(fil_info, dict) else None
        if not isinstance(url, str) or not url:
            raise BusinessError(
                f"Filfeltet {element!r} er udfyldt, men svaret har intet link "
                "til filen i data.linked"
            )

        try:
            fil = os2forms.fetch_attachment(url, api_key)
        except os2forms.OS2FormsNotFound as e:
            raise BusinessError(
                f"Den uploadede fil i {element!r} findes ikke i OS2Forms"
            ) from e
        except os2forms.OS2FormsError as e:
            raise ProcessError(str(e)) from e

        navn = _filnavn(url, element)
        blokke.append(
            remote_post.Filblok(
                blok=blok,
                fil_id=fil_id,
                navn=navn,
                mime=_mime(fil_info, navn, fil.content_type),
                indhold=fil.indhold,
            )
        )
    return blokke


def handle_item(item_data: dict, item_reference: str) -> str:
    """Sender ét formularsvar fra OS2Forms til aktindsigt.

    Args:
        item_data: Itemets data fra polling-servicen. Bruges kun til at finde
            webformens id; svaret hentes altid friskt.
        item_reference: Itemets reference: svarets uuid.

    Returns:
        Beskeden, itemet afsluttes med.

    Raises:
        BusinessError: Ved en fejl, en medarbejder skal håndtere.
        ProcessError: Hvis OS2Forms eller aktindsigt ikke kunne spørges.
    """
    if not item_reference:
        raise BusinessError("Itemet har ingen reference (svarets uuid)")

    webform_id = webform_id_fra_data(item_data)
    if webform_id is None:
        raise BusinessError("Itemets data angiver ingen webform")
    config = intake_config.WEBFORMS.get(webform_id)
    if config is None:
        kendte = ", ".join(sorted(intake_config.WEBFORMS))
        raise BusinessError(
            f"Webformen {webform_id!r} sendes ikke til aktindsigt. Kendte: {kendte}"
        )

    os2forms_key = _credential(intake_config.OS2FORMS_CREDENTIAL)
    try:
        svar = os2forms.fetch_submission(webform_id, item_reference, os2forms_key)
    except os2forms.OS2FormsNotFound as e:
        raise BusinessError(
            f"Svaret {item_reference} findes ikke i OS2Forms ({webform_id})"
        ) from e
    except os2forms.OS2FormsError as e:
        raise ProcessError(str(e)) from e

    data = svar.get("data")
    if not isinstance(data, dict):
        raise BusinessError(f"Svaret {item_reference} har ingen formulardata")

    filblokke = hent_filblokke(data, config, os2forms_key)
    items = remote_post.build_form_items(webform_id, item_reference, data, filblokke)

    try:
        modtaget = aktindsigt.send_sag(
            items, _credential(intake_config.AKTINDSIGT_CREDENTIAL)
        )
    except aktindsigt.AktindsigtAfvist as e:
        raise BusinessError(f"Aktindsigt afviste indsendelsen (422): {e}") from e
    except aktindsigt.AktindsigtFejl as e:
        raise ProcessError(str(e)) from e

    if modtaget.ny:
        besked = f"Sag {modtaget.sag_id} oprettet i aktindsigt"
    else:
        besked = f"Allerede modtaget i aktindsigt som sag {modtaget.sag_id}"
    logger.info("%s: %s", item_reference, besked)
    return besked
