import html
import json
import os
import time
import traceback

from loguru import logger
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from todoist_api_python.api import TodoistAPI

from helper.config_helper import CHAT_ID
from quarter_lib.akeyless import get_secrets

TODOIST_TOKEN = get_secrets("todoist/token")
TODOIST_API = TodoistAPI(TODOIST_TOKEN)
MAX_LENGTH_PER_MESSAGE = 4096

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    logger.error("Exception while handling an update:" + str(context.error))

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f"An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    if len(message) < MAX_LENGTH_PER_MESSAGE:
        await context.bot.send_message(
            chat_id=CHAT_ID, text=message, parse_mode=ParseMode.HTML
        )
    else:
        messages_needed = len(message) // MAX_LENGTH_PER_MESSAGE + 1
        for i in range(messages_needed):
            temp = message[i * MAX_LENGTH_PER_MESSAGE: (i + 1) * MAX_LENGTH_PER_MESSAGE]
            await context.bot.send_message(
                chat_id=CHAT_ID, text=temp, parse_mode=ParseMode.HTML
            )
    time.sleep(5)
