from src.helper.telegram_helper import retry_on_error


async def log_to_telegram(message, logger, update):
	logger.info(message)
	await retry_on_error(update.message.reply_text, retry=5, wait=0.1, text=message)
