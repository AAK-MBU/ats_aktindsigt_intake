"""
This is the main entry point for the process
"""

import asyncio
import logging
import sys

from automation_server_client import AutomationServer, Workqueue
from dotenv import load_dotenv
from mbu_rpa_core.exceptions import BusinessError, ProcessError
from mbu_rpa_core.process_states import CompletedState

from ats_framework.core.application_handler import close, reset, startup
from ats_framework.core.error_handling import ErrorContext, handle_error
from ats_framework.core.finalize_process import finalize_process
from ats_framework.core.process_item import process_item
from ats_framework.helpers import ats_functions, config
from ats_framework.processes import intake_config

logger = logging.getLogger(__name__)


async def populate_queue(workqueue: Workqueue):
    """Fylder ikke køen: os2forms-polling-service lægger svarene på den."""

    logger.info(
        "Workqueue %s is populated by os2forms-polling-service; nothing to add.",
        workqueue.name,
    )


async def process_workqueue(workqueue: Workqueue):
    """Process items from the workqueue."""

    logger.info("Processing workqueue...")

    intake_config.validate_config()
    startup()

    error_count = 0

    while error_count < config.MAX_RETRY:
        for item in workqueue:
            try:
                with item:
                    data, reference = ats_functions.get_item_info(item)

                    try:
                        logger.info("Processing item with reference: %s", reference)
                        message = process_item(data, reference)

                        completed_state = CompletedState.completed(message)
                        item.complete(str(completed_state))

                        continue

                    except BusinessError as e:
                        context = ErrorContext(
                            item=item,
                            action=item.pending_user,
                            send_mail=False,
                            process_name=workqueue.name,
                        )
                        handle_error(
                            error=e,
                            log=logger.info,
                            context=context,
                        )

                    except Exception as e:
                        pe = ProcessError(str(e))
                        raise pe from e

            except ProcessError as e:
                context = ErrorContext(
                    item=item,
                    action=item.fail,
                    send_mail=True,
                    process_name=workqueue.name,
                )
                handle_error(
                    error=e,
                    log=logger.error,
                    context=context,
                )
                error_count += 1
                reset()

        break

    logger.info("Finished processing workqueue.")
    close()


async def finalize(workqueue: Workqueue):
    """Finalize process."""

    logger.info("Finalizing process...")

    try:
        finalize_process()
        logger.info("Finished finalizing process.")

    except BusinessError as e:
        handle_error(error=e, log=logger.info)

    except Exception as e:
        pe = ProcessError(str(e))
        context = ErrorContext(
            send_mail=True,
            process_name=workqueue.name,
        )
        handle_error(error=pe, log=logger.error, context=context)

        raise pe from e


if __name__ == "__main__":
    ats_functions.init_logger()
    load_dotenv()
    config.apply_ca_bundle()

    ats = AutomationServer.from_environment()

    prod_workqueue = ats.workqueue()
    process = ats.process

    if "--queue" in sys.argv:
        asyncio.run(populate_queue(prod_workqueue))

    if "--process" in sys.argv:
        asyncio.run(process_workqueue(prod_workqueue))

    if "--finalize" in sys.argv:
        asyncio.run(finalize(prod_workqueue))

    sys.exit(0)
