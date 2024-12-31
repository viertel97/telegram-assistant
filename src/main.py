from quarter_lib.akeyless import get_secrets # noqa: F401
from quarter_lib.logging import setup_logging
from telegram import Update
from telegram.ext import (
	Application,
	CallbackContext,
	CallbackQueryHandler,
	CommandHandler,
	MessageHandler,
	filters,
)

from handler.audio_handler import handle_audio
from handler.command_handler import (
	add_splitwise_placeholder,
	dump_todoist_to_monica,
	dump_todoist_to_monica_v2,
	toggle_cloudflare_ips,
	wol,
)
from handler.document_handler import handle_document
from handler.error_handler import handle_error
from handler.text_handler import handle_text
from handler.video_handler import video_to_text
from handler.voice_handler import voice_to_text
from services.conversation_service import get_last_calls, transcribe_call_from_one_drive

logger = setup_logging(__file__)

TELEGRAM_TOKEN = get_secrets("telegram/token")


async def start(update: Update, context: CallbackContext):
	await update.message.reply_text(text="Do Stuff.")


def get_command_handler():
	return (
		CommandHandler("start", start),
		CommandHandler("wol", wol),
		CommandHandler("dump_todoist_to_monica", dump_todoist_to_monica),
		CommandHandler("dump_todoist_to_monica_v2", dump_todoist_to_monica_v2),
		CommandHandler("toggle_cloudflare_ips", toggle_cloudflare_ips),
		CommandHandler("add_splitwise_placeholder", add_splitwise_placeholder),
		CommandHandler("transcribe_call", get_last_calls),
	)


def get_conversation_handler():
	return (CallbackQueryHandler(transcribe_call_from_one_drive),)


def get_message_handler():
	return (
		MessageHandler(filters.VOICE, voice_to_text),
		MessageHandler(filters.VIDEO, video_to_text),
		MessageHandler(filters.Document.ALL, handle_document),
		MessageHandler(filters.AUDIO, handle_audio),
		MessageHandler(filters.TEXT, handle_text),
	)


def main():
	application = Application.builder().token(TELEGRAM_TOKEN).build()

	[
		application.add_handler(
			handler,
		)
		for handler in get_command_handler() + get_message_handler() + get_conversation_handler()
	]
	application.add_error_handler(handle_error)
	logger.info("Start polling")
	application.run_polling()


if __name__ == "__main__":
	main()
