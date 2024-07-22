import telegram.ext.filters as filters
from quarter_lib.logging import setup_logging
from telegram import Update
from telegram.ext import Application, CallbackContext, CommandHandler, MessageHandler

from handler.audio_handler import handle_audio
from handler.command_handler import wol, dump_todoist_to_monica, toggle_cloudflare_ips, add_splitwise_placeholder
from handler.document_handler import handle_document
from handler.error_handler import handle_error
from handler.video_handler import video_to_text
from handler.voice_handler import voice_to_text

logger = setup_logging(__file__)

TELEGRAM_TOKEN = get_secrets("telegram/token")


async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(text="Do Stuff.")


def get_command_handler():
    return (
        CommandHandler(str("start"), start),
        CommandHandler(str("wol"), wol),
        CommandHandler(str("dump_todoist_to_monica"), dump_todoist_to_monica),
        CommandHandler(str("toggle_cloudflare_ips"), toggle_cloudflare_ips),
        CommandHandler(str("add_splitwise_placeholder"), add_splitwise_placeholder),
    )


def get_message_handler():
    return (
        MessageHandler(filters.VOICE, voice_to_text),
        MessageHandler(filters.VIDEO, video_to_text),
        MessageHandler(filters.Document.ALL, handle_document),
        MessageHandler(filters.AUDIO, handle_audio),
    )


def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    [
        application.add_handler(
            handler,
        )
        for handler in get_command_handler() + get_message_handler()  # + get_conversation_handler()
    ]
    application.add_error_handler(handle_error)
    logger.info("Start polling")
    application.run_polling()


if __name__ == "__main__":
    main()
