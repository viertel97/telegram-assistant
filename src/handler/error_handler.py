import html
import json
import time
import traceback

from quarter_lib.akeyless import get_secrets
from quarter_lib.logging import setup_logging
from telegram import Update
from telegram.ext import ContextTypes
from todoist_api_python.api import TodoistAPI

from src.helper.config_helper import CHAT_ID
from src.helper.telegram_helper import send_long_message

TODOIST_TOKEN = get_secrets("todoist/token")
TODOIST_API = TodoistAPI(TODOIST_TOKEN)

logger = setup_logging(__file__)


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
	await send_long_message(message, context.bot.send_message, chat_id=CHAT_ID)
	time.sleep(5)
