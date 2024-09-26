import os
import urllib.parse

import msal
import requests
from quarter_lib.akeyless import get_secrets
from quarter_lib.logging import setup_logging

logger = setup_logging(__file__)

base_url = "https://graph.microsoft.com/v1.0/"

AUTHORITY_URL = "https://login.microsoftonline.com/consumers/"

SCOPES = ["User.Read", "Files.ReadWrite.All"]

CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN = get_secrets(
    ["microsoft/client_id", "microsoft/client_secret", "microsoft/refresh_token"])

client_instance = msal.ConfidentialClientApplication(
    client_id=CLIENT_ID,
    client_credential=CLIENT_SECRET,
    authority=AUTHORITY_URL
)


def get_access_token():
    token = client_instance.acquire_token_by_refresh_token(
        refresh_token=REFRESH_TOKEN,
        scopes=SCOPES)
    return token['access_token']


def download_file_from_path(path, file_name):
    access_token = get_access_token()

    headers = {'Authorization': 'Bearer ' + access_token}
    url = base_url + "me/drive/root:/" + path
    url = urllib.parse.quote(url, safe=':/')
    logger.info("get file from path: " + url)
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        # Save the file in the disk
        with open(file_name, 'wb') as file:
            file.write(response.content)
        logger.info("file {} saved".format(file_name))
    else:
        logger.error("Error while getting file from path: " + url)
        logger.error(response.status_code)
        logger.error(response.text)
        raise Exception("Error while getting file from path: " + url)
    return file_name


def get_file_list(path, access_token):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    url = base_url + f"me/drive/root:/" + '/'.join(path.split("/")) + ":/"
    logger.info("get file list from path: " + url)
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception("Error getting file list", response.text)
    destination_folder_id = response.json()['id']
    list_files_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{destination_folder_id}/children"

    response = requests.get(list_files_url, headers=headers)
    return response.json(), destination_folder_id


def copy_file(file_id, original_file_name, access_token):
    copy_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/copy"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    body = {
        "name": original_file_name + "_backup"
    }
    response = requests.post(copy_url, headers=headers, json=body)
    if response.status_code == 202:
        return response
    else:
        raise Exception("Error copying file")


def create_backup(path, access_token):
    folder_path = os.path.dirname(path)
    logger.info("folder path: " + folder_path)
    file_list, destination_folder_id = get_file_list(folder_path, access_token)
    logger.info("file list: " + str(file_list))
    for file in file_list['value']:
        if file['name'] == os.path.basename(path):
            file_id = file['id']
            break
    # check if variable file_id is set
    if 'file_id' not in locals():
        raise Exception("File not found")
    copy_result = copy_file(file_id, os.path.basename(path), access_token)
    logger.info("copy result: " + str(copy_result.json()))
    return destination_folder_id


def upload_file(local_file_path, onedrive_file_path, destination_folder_id, access_token):
    file_name = os.path.basename(onedrive_file_path)
    upload_url = f"https://graph.microsoft.com/v1.0/drive/items/{destination_folder_id}:/{file_name}:/content"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/octet-stream"  # Set the content-type to octet-stream for file upload
    }

    with open(local_file_path, "rb") as file:
        response = requests.put(upload_url, headers=headers, data=file)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception("Error uploading file")


def replace_file_in_onedrive(onedrive_file_path, local_file_path):
    access_token = get_access_token()
    logger.info("Creating backup of file {}  in onedrive".format(onedrive_file_path))
    destination_folder_id = create_backup(onedrive_file_path, access_token)
    logger.info("Backup of file {} created in onedrive".format(onedrive_file_path))
    upload_result = upload_file(local_file_path, onedrive_file_path, destination_folder_id, access_token)
    logger.info("Local file {} replaced onedrive file {}".format(local_file_path, onedrive_file_path))
