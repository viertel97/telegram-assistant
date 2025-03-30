import os
import re
import unicodedata

from quarter_lib.logging import setup_logging

logger = setup_logging(__file__)


def delete_files(files):
	for file in files:
		try:
			os.remove(file)
		except FileNotFoundError:
			logger.error("Error while deleting file : ", str(file))


def slugify(value, allow_unicode=False):
	value = str(value)
	if allow_unicode:
		value = unicodedata.normalize("NFKC", value)
	else:
		value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
	value = re.sub(r"[^\w\s-]", "", value.lower())
	value = re.sub(r"[-\s]+", "-", value).strip("-_")
	if len(value) > 40:
		return value[:40]
	return value
