"""Aktindsigts egen læsning af en intake-indsendelse, til brug i tests.

Kopi af de rene funktioner ``parse_felter`` og filblok-afkodningen i
``aktindsigtapp/backend/app/services/webform_mapping_service.py``. Testene
bruger dem til at bevise, at den krop, processen bygger, læses af aktindsigt
som Remote post-kroppen blev. Ændres aktindsigts læsning, skal kopien følge med.
"""

import base64
import re
from collections.abc import Iterable

_BRACKET_RE = re.compile(r"^(?P<navn>[^\[\]]+)\[(?P<noegle>[^\[\]]*)\]$")


def parse_felter(items: Iterable[tuple[str, str]]) -> dict[str, object]:
    """Folder flade feltnavne ud til lister og blokke, som aktindsigt gør.

    Args:
        items: ``(navn, værdi)``-par i indsendelsens rækkefølge.

    Returns:
        Feltnavn mappet til ``str``, ``list[str]`` eller ``dict[str, str]``.
    """
    flade: dict[str, object] = {}
    lister: dict[str, dict[int, str]] = {}

    for navn, vaerdi in items:
        m = _BRACKET_RE.match(navn)
        if not m:
            flade[navn] = vaerdi
            continue

        base, noegle = m.group("navn"), m.group("noegle")
        if noegle.isdigit():
            lister.setdefault(base, {})[int(noegle)] = vaerdi
        else:
            blok = flade.setdefault(base, {})
            if isinstance(blok, dict):
                blok[noegle] = vaerdi

    for base, indekseret in lister.items():
        flade[base] = [indekseret[i] for i in sorted(indekseret)]

    return flade


def fuldmagt_bytes(felter: dict[str, object], blok_navn: str) -> bytes | None:
    """Afkoder en filblok, som aktindsigts ``fuldmagt_fra_felter`` gør.

    Args:
        felter: Felterne fra :func:`parse_felter`.
        blok_navn: Filblokkens navn, fx ``_upload_fuldmagt``.

    Returns:
        Filens bytes, eller ``None`` hvis blokken mangler eller er uden data.
    """
    blok = felter.get(blok_navn)
    if not isinstance(blok, dict):
        return None
    raw = (blok.get("data") or "").strip()
    if not raw:
        return None
    return base64.b64decode(raw, validate=True)
