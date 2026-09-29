"""Module to handle item processing"""

from ats_framework.processes.handle_item import handle_item


def process_item(item_data: dict, item_reference: str) -> str:
    """Behandler ét item og returnerer beskeden, det afsluttes med."""
    return handle_item(item_data, item_reference)
