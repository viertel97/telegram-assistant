from telegram import Update
from telegram.ext import CallbackContext

from services.grabber_service import dump_todoist_to_monica as dump
from services.notion_service import stretch_TPT as stretch
from services.transcriber_service import separate_audibooks
from services.wol_service import start_pc_via_wol


async def wol(update: Update, context: CallbackContext):
    await start_pc_via_wol(update, context)


async def separate(update: Update, context: CallbackContext):
    await separate_audibooks(update, context)


async def dump_todoist_to_monica(update: Update, context: CallbackContext):
    await dump(update, context)


async def stretch_TPT(update: Update, context: CallbackContext):
    await stretch(update, context)
