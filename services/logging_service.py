async def log_to_telegram(message, logger, update):
    logger.info(message)
    await update.message.reply_text(text=message,disable_notification=True)
