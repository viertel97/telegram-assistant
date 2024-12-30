from quarter_lib.logging import setup_logging

logger = setup_logging(__file__)
import os


def delete_files(files):
	for file in files:
		try:
			os.remove(file)
		except:
			logger.error("Error while deleting file : ", file)
