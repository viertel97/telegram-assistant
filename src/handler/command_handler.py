from telegram import Update
from telegram.ext import CallbackContext

from src.helper.config_helper import is_not_correct_chat_id
from src.services.cloudflare_service import toggle_ips
from src.services.conversation_service import transcribe_call_from_one_drive
from src.services.grabber_service_v2 import dump_todoist_to_monica as dump_v2
from src.services.splitwise_service import add_placeholder_to_splitwise
from src.services.wol_service import start_pc_via_wol


async def wol(update: Update, context: CallbackContext):
	if is_not_correct_chat_id(update.message.chat_id):
		await update.message.reply_text("Nah")
		return
	await start_pc_via_wol(update, context)


async def dump_todoist_to_monica_v2(update: Update, context: CallbackContext):
	if is_not_correct_chat_id(update.message.chat_id):
		await update.message.reply_text("Nah")
		return
	await dump_v2(update, context)


async def toggle_cloudflare_ips(update: Update, context: CallbackContext):
	if is_not_correct_chat_id(update.message.chat_id):
		await update.message.reply_text("Nah")
		return
	await toggle_ips(update, context)


async def add_splitwise_placeholder(update: Update, context: CallbackContext):
	if is_not_correct_chat_id(update.message.chat_id):
		await update.message.reply_text("Nah")
		return
	await add_placeholder_to_splitwise(update, context)


async def transcribe_call(update: Update, context: CallbackContext):
	if is_not_correct_chat_id(update.message.chat_id):
		await update.message.reply_text("Nah")
		return
	await transcribe_call_from_one_drive(update, context)
