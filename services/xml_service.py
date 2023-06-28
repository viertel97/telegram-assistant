import os
import xml.etree.ElementTree as ET

from loguru import logger

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)


def xml_to_dict(data):
    root = ET.XML(data)
    data = []
    for item in root.findall('./bookmark'):  # find all projects node
        data_dict = {}  # dictionary to store content of each projects
        data_dict.update(item.attrib)  # make panelist_login the first key of the dict
        for child in item:
            data_dict[child.tag] = child.text
        data.append(data_dict)
    return data
