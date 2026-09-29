"""Bygger den urlencoded indsendelse, aktindsigts intake forventer.

Aktindsigts ``POST /api/intake/sager`` læser præcis den form, OS2Forms'
Remote post-handler sendte: ``application/x-www-form-urlencoded`` med
formularens elementnavne som feltnavne. Sammensatte værdier kodes som PHP's
``http_build_query`` gør det:

- en liste bliver til ``navn[0]``, ``navn[1]`` …
- en dict bliver til ``navn[nøgle]``
- ``None`` udelades, ``True``/``False`` bliver ``"1"``/``"0"``

En fil sendes som blokken ``_<element>[id|name|mime|data]`` med filens bytes
base64-kodet i ``data``. Dertil kommer ``webform_id``, som vælger aktindsigts
omkodning, og ``submission_uuid``, som gør kaldet idempotent.

Modulet er rent: ingen netværk, ingen logning af indhold.
"""

import base64
from collections.abc import Iterator
from dataclasses import dataclass

# Nøglen i webform_rest-svarets ``data``, der bærer vedhæftningernes links. Den
# er ikke et formularfelt og sendes ikke med.
ATTACHMENTS_KEY = "attachments"

WEBFORM_ID_FELT = "webform_id"
SUBMISSION_UUID_FELT = "submission_uuid"


@dataclass(frozen=True)
class Filblok:
    """En vedhæftning, som den sendes i en Remote post-filblok.

    Attributes:
        blok: Blokkens navn, fx ``_upload_fuldmagt``.
        fil_id: Filens id i OS2Forms (elementets værdi i ``data``).
        navn: Filnavnet.
        mime: Filens mime-type.
        indhold: Filens bytes.
    """

    blok: str
    fil_id: str
    navn: str
    mime: str
    indhold: bytes


def _skalar(value: object) -> str:
    """Koder en enkelt værdi som ``http_build_query``.

    Args:
        value: Værdien. Ikke ``None``, ikke en liste eller dict.

    Returns:
        ``"1"``/``"0"`` for booleans, ellers ``str(value)``.
    """
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


def flatten(name: str, value: object) -> Iterator[tuple[str, str]]:
    """Folder en værdi ud til flade ``(feltnavn, værdi)``-par.

    Args:
        name: Feltnavnet, værdien står under.
        value: Værdien: skalar, liste, dict eller ``None``.

    Yields:
        ``(feltnavn, værdi)`` i samme rækkefølge som ``http_build_query``.
        En tom liste eller dict og ``None`` giver ingen par.
    """
    if value is None:
        return
    if isinstance(value, dict):
        for key, sub in value.items():
            yield from flatten(f"{name}[{key}]", sub)
    elif isinstance(value, list | tuple):
        for index, sub in enumerate(value):
            yield from flatten(f"{name}[{index}]", sub)
    else:
        yield name, _skalar(value)


def build_form_items(
    webform_id: str,
    submission_uuid: str,
    data: dict,
    filblokke: list[Filblok],
) -> list[tuple[str, str]]:
    """Bygger indsendelsens felter i den rækkefølge, de sendes.

    Args:
        webform_id: Webformens maskinnavn.
        submission_uuid: Svarets uuid (workitem'ets reference).
        data: ``data`` fra webform_rest-svaret. ``attachments`` springes
            over; de øvrige nøgler sendes som felter.
        filblokke: De hentede vedhæftninger.

    Returns:
        ``(feltnavn, værdi)``-par. ``webform_id`` står først og
        ``submission_uuid`` sidst, så de vinder over et felt i ``data`` med
        samme navn (aktindsigt lader det sidste af to ens navne vinde).
    """
    items: list[tuple[str, str]] = [(WEBFORM_ID_FELT, webform_id)]
    for key, value in data.items():
        if key in (ATTACHMENTS_KEY, WEBFORM_ID_FELT, SUBMISSION_UUID_FELT):
            continue
        items.extend(flatten(key, value))
    for fil in filblokke:
        items.extend(
            [
                (f"{fil.blok}[id]", fil.fil_id),
                (f"{fil.blok}[name]", fil.navn),
                (f"{fil.blok}[mime]", fil.mime),
                (f"{fil.blok}[data]", base64.b64encode(fil.indhold).decode("ascii")),
            ]
        )
    items.append((SUBMISSION_UUID_FELT, submission_uuid))
    return items
