"""Hjælpefunktioner til Automation Server-workitems og logning."""

import logging

from automation_server_client import WorkItem


def get_item_info(item: WorkItem) -> tuple[dict, str]:
    """Udpakker et workitems data og reference.

    Polling-servicen lægger items på køen med ``POST /workqueues/{id}/add``
    og ``{"data": <payload>, "reference": <svarets uuid>}``, så ``item.data``
    er payloaden selv.

    Args:
        item: Workitem'et fra intake-køen.

    Returns:
        ``(data, reference)``. ``data`` er en tom dict, hvis itemet ingen data
        har.
    """
    data = item.data if isinstance(item.data, dict) else {}
    return data, str(item.reference or "")


def init_logger() -> None:
    """Sætter rodloggeren op med tidsstempel, niveau og kildeplacering."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(module)s.%(funcName)s:%(lineno)d — %(message)s",
        datefmt="%H:%M:%S",
    )
