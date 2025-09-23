import time

from quarter_lib.logging import setup_logging
from telegram.constants import ParseMode
from telegram.error import NetworkError

logger = setup_logging(__file__)

MAX_LENGTH_PER_MESSAGE = 4096 - 50


async def retry_on_error(func, wait=0.1, retry=0, *args, **kwargs):
	i = 0
	while True:
		try:
			return await func(*args, **kwargs)
		except NetworkError as e:
			logger.error(e)
			logger.error(f"Network Error. Retrying...{i}")
			i += 1
			time.sleep(wait)
			if retry != 0 and i == retry:
				break


async def send_long_message(message, send_function, **kwargs):
	if len(message) < MAX_LENGTH_PER_MESSAGE:
		await send_function(text=message, parse_mode=ParseMode.HTML, disable_notification=True, **kwargs)
	else:
		messages_needed = len(message) // MAX_LENGTH_PER_MESSAGE + 1
		for i in range(messages_needed):
			temp = message[i * MAX_LENGTH_PER_MESSAGE : (i + 1) * MAX_LENGTH_PER_MESSAGE]
			await send_function(text=temp, parse_mode=ParseMode.HTML, disable_notification=True, **kwargs)
			time.sleep(5)
