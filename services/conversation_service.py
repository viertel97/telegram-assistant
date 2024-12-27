import os

from dateutil import parser
from quarter_lib.logging import setup_logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext

from helper.config_helper import is_not_correct_chat_id
from services.groq_service import transcribe_groq
from services.microsoft_service import (
    get_access_token,
    get_file_list,
    download_file_by_id,
)

logger = setup_logging(__file__)


async def get_last_calls(update: Update, context: CallbackContext):
    if is_not_correct_chat_id(update.message.chat_id):
        await update.message.reply_text("Nah")
        return

    access_token = get_access_token()

    files, destination_folder_id = get_file_list(
        "Anwendungen/Call Recorder - SKVALEX", access_token
    )
    files = [file for file in files if "@microsoft.graph.downloadUrl" in file.keys()]
    for file in files:
        file["sortCreatedDatetime"] = parser.parse(file["createdDateTime"])

    files = sorted(files, key=lambda x: x["sortCreatedDatetime"], reverse=True)

    reply_keyboard = [
        [InlineKeyboardButton(file["name"], callback_data=str(file["id"]))]
        for file in files[:20]
    ]
    reply_markup = InlineKeyboardMarkup(reply_keyboard)

    await update.message.reply_text("Please choose:", reply_markup=reply_markup)


async def transcribe_call_from_one_drive(update: Update, context: CallbackContext):
    logger.info("start: Call to text")
    query = update.callback_query
    file_id = query.data

    await query.answer()

    data = dict()
    for inline_keyboard in query.message.reply_markup.inline_keyboard:
        if inline_keyboard[0].callback_data == file_id:
            data.update({"id": file_id, "name": inline_keyboard[0].text})

    await query.edit_message_text(
        text=f"Selected option: {data['name']} ({data['id']})"
    )

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Downloading file {data['name']} and start transcribing",
    )
    download_file_by_id(data["id"], "input.wav")

    await transcribe_groq(
        "input.wav", context.bot.send_message, chat_id=update.effective_chat.id
    )

    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=f"Done transcribing of {data['name']}"
    )
    os.remove("input.wav")
