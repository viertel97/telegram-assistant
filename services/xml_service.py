import xml.etree.ElementTree as ET

from quarter_lib.logging import setup_logging

logger = setup_logging(__file__)


def xml_to_dict(data):
    root = ET.XML(data)
    data = []
    for item in root.findall('./bookmark'):  # find all projects node
        data_dict = {}  # dictionary to store content of each projects
        data_dict.update(item.attrib)  # make panelist_login the first key of the dict
        for child in item:
            data_dict[child.tag] = child.text
        data.append(data_dict)
    logger.info("found {} bookmarks in xml".format(len(data)))
    logger.info(data)
    return data
