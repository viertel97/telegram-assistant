import math
import time
from datetime import timedelta

from telegram import Update

from src.helper.telegram_helper import send_long_message

VOICE_RECORDER_MATCH = r"^(([1-9]|[0-2]\d|[3][0-1])\.([1-9]|[0]\d|[1][0-2])\.[2][0]\d{2})$|^(([1-9]|[0-2]\d|[3][0-1])\.([1-9]|[0]\d|[1][0-2])\.[2][0]\d{2}\s([1-9]|[0-1]\d|[2][0-3])\:[0-5]\d.*)$"
EASY_VOICE_RECORDER_MATCH = ".+was recorded during meditation at.+"
GHT_MATCH = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\+\d{2}:\d{2}: "
DEFAULT_OFFSET = timedelta(hours=2)


def is_nan_or_none(value):
	return value is None or (isinstance(value, float) and math.isnan(value))


async def return_content(content: list, intro: str, update: Update):
	if content is not None:
		content = "\n".join(f"* {task}" for task in content)
		await update.message.reply_text(f"{intro}: \n\n")
		await send_long_message(content, update.message.reply_text)
		time.sleep(5)
	else:
		await update.message.reply_text(f"No {intro} found")
