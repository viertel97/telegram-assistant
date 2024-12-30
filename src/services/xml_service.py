import xml.etree.ElementTree as ET

from quarter_lib.logging import setup_logging
from telegram import Update

from src.services.logging_service import log_to_telegram

logger = setup_logging(__file__)


async def xml_to_dict(data, update:Update) -> list:
	root = ET.XML(data)
	data = []
	for item in root.findall("./bookmark"):  # find all projects node
		data_dict = {}  # dictionary to store content of each projects
		data_dict.update(item.attrib)  # make panelist_login the first key of the dict
		for child in item:
			data_dict[child.tag] = child.text
		data.append(data_dict)
	await log_to_telegram(f"found {len(data)} bookmarks in xml", logger, update)
	logger.info(data)
	return data
