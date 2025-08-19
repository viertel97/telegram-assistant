import os
import urllib.parse

import msal
import requests
from quarter_lib.akeyless import get_secrets
from quarter_lib.logging import setup_logging

logger = setup_logging(__file__)

base_url = "https://graph.microsoft.com/v1.0/"

AUTHORITY_URL = "https://login.microsoftonline.com/consumers/"

SCOPES = [
    "Files.ReadWrite.All",
    "Files.Read.All",
    "Notes.ReadWrite",
    "Notes.ReadWrite.All",
    "Notes.Read.All",
    "User.Read",
]

CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN = get_secrets(["microsoft/client_id", "microsoft/client_secret", "microsoft/refresh_token"])

client_instance = msal.ConfidentialClientApplication(client_id=CLIENT_ID, client_credential=CLIENT_SECRET, authority=AUTHORITY_URL)


def get_access_token():
    token = client_instance.acquire_token_by_refresh_token(refresh_token=REFRESH_TOKEN, scopes=SCOPES)
    return token["access_token"]


def download_file_from_path(path, file_name):
    access_token = get_access_token()

    headers = {"Authorization": "Bearer " + access_token}
    url = base_url + "me/drive/root:/" + path
    url = urllib.parse.quote(url, safe=":/")
    logger.info("get file from path: " + url)
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        # Save the file in the disk
        with open(file_name, "wb") as file:
            file.write(response.content)
        logger.info(f"file {file_name} saved")
    else:
        logger.error("Error while getting file from path: " + url)
        logger.error(response.status_code)
        logger.error(response.text)
        raise Exception("Error while getting file from path: " + url)
    return file_name

def download_pdf_from_path(path, file_name):
    access_token = get_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    url = urllib.parse.quote(f"{base_url}me/drive/root:/{path}", safe=":/")
    logger.info(f"Fetching file from path: {url}")

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        logger.error(f"Failed to fetch file: {response.status_code}, {response.text}")
        raise Exception(f"Error fetching file from path: {url}")

    download_url = response.json().get('@microsoft.graph.downloadUrl')
    pdf_response = requests.get(download_url)
    if pdf_response.status_code != 200:
        logger.error(f"Failed to download PDF: {pdf_response.status_code}, {pdf_response.text}")
        raise Exception(f"Error downloading PDF from path: {url}")

    with open(file_name, "wb") as file:
        file.write(pdf_response.content)
    logger.info(f"File {file_name} saved successfully")

    return file_name

def download_file_by_id(file_id, file_name):
    access_token = get_access_token()

    headers = {"Authorization": "Bearer " + access_token}
    url = base_url + "me/drive/items/" + file_id + "/content"
    logger.info("get file from path: " + url)
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        # Save the file in the disk
        with open(file_name, "wb") as file:
            file.write(response.content)
        logger.info(f"file {file_name} saved")
    else:
        logger.error("Error while getting file from path: " + url)
        logger.error(response.status_code)
        logger.error(response.text)
        raise Exception("Error while getting file from path: " + url)


def get_file_list(path, access_token):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    url = f"{base_url}me/drive/root:/{'/'.join(path.split('/'))}:/"
    url = urllib.parse.quote(url, safe=":/")
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception("Error getting file list", response.text)
    destination_folder_id = response.json()["id"]
    list_files_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{destination_folder_id}/children"

    files = []
    while list_files_url:
        resp_json = requests.get(list_files_url, headers=headers).json()
        files.extend(resp_json.get("value", []))
        list_files_url = resp_json.get("@odata.nextLink")

    return files, destination_folder_id


def copy_file(file_id, original_file_name, access_token, file_list):
    copy_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/copy"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Check for existing backups and generate unique name
    base_name = os.path.splitext(original_file_name)[0]
    extension = os.path.splitext(original_file_name)[1]
    backup_name = f"{base_name}_backup{extension}"


    existing_names = [f["name"] for f in file_list]

    # Find unique backup name
    counter = 1
    while backup_name in existing_names:
        backup_name = f"{base_name}_backup_{counter}{extension}"
        counter += 1

    body = {"name": backup_name}
    response = requests.post(copy_url, headers=headers, json=body)
    if response.status_code == 202:
        return response
    raise Exception("Error copying file")


def create_backup(path, access_token):
    folder_path = os.path.dirname(path)
    logger.info("folder path: " + folder_path)
    file_list, destination_folder_id = get_file_list(folder_path, access_token)
    logger.info("file list: " + str(file_list))
    file_id = None
    for file in file_list:
        if file["name"] == os.path.basename(path):
            file_id = file["id"]
            break
    # check if variable file_id is set
    if not file_id:
        raise Exception("File not found")
    copy_result = copy_file(file_id, os.path.basename(path), access_token, file_list)
    logger.info("copy result: " + str(copy_result))
    return destination_folder_id


def upload_file(local_file_path, onedrive_file_path, destination_folder_id, access_token):
    file_name = os.path.basename(onedrive_file_path)
    upload_url = f"https://graph.microsoft.com/v1.0/drive/items/{destination_folder_id}:/{file_name}:/content"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/octet-stream",  # Set the content-type to octet-stream for file upload
    }

    with open(local_file_path, "rb") as file:
        response = requests.put(upload_url, headers=headers, data=file)
    if response.status_code == 200:
        return response.json()
    raise Exception("Error uploading file")


def replace_file_in_onedrive(onedrive_file_path, local_file_path):
    access_token = get_access_token()
    logger.info(f"Creating backup of file {onedrive_file_path}  in onedrive")
    destination_folder_id = create_backup(onedrive_file_path, access_token)
    logger.info(f"Backup of file {onedrive_file_path} created in onedrive")
    upload_result = upload_file(local_file_path, onedrive_file_path, destination_folder_id, access_token)
    logger.info(f"Local file {local_file_path} replaced onedrive file {onedrive_file_path}")


def search_files_combined(path, search_term, extension, recursive=True):
    """Search for files with both name filter and extension filter"""
    try:
        results = search_files_in_path(path, search_term=search_term, file_extension=extension, recursive=recursive)
        search_type = "recursively" if recursive else "in current folder only"
        print(f"Found {len(results)} {extension} files containing '{search_term}' {search_type} in '{path}':")
        for file in results:
            print(f"  - {file['name']}")
            print(f"    Path: {file['path']}")
            print(f"    Created: {file['created_datetime']}")
            print(f"    Modified: {file['modified_datetime']}")
            print(f"    Size: {file['size']} bytes")
            print()
        return results
    except Exception as e:
        print(f"Error in combined search: {e}")
        return []


def search_files_in_path(path, search_term=None, file_extension=None, recursive=True):
    """
    Search for files in a specific OneDrive path.

    Args:
        path (str): OneDrive path to search in (e.g., "Documents/MyFolder")
        search_term (str, optional): Search term to filter file names
        file_extension (str, optional): File extension to filter by (e.g., ".pdf", ".docx")
        recursive (bool): Whether to search recursively in subfolders (default: True)

    Returns:
        list: List of matching files with their metadata
    """
    access_token = get_access_token()

    def search_folder_recursive(folder_path, current_folder_id=None):
        """Recursively search through folders"""
        matching_files = []

        try:
            if current_folder_id:
                # Use folder ID for API call
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                }
                list_files_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{current_folder_id}/children"

                files = []
                while list_files_url:
                    resp_json = requests.get(list_files_url, headers=headers).json()
                    files.extend(resp_json.get("value", []))
                    list_files_url = resp_json.get("@odata.nextLink")
            else:
                # Use path for initial call
                files, folder_id = get_file_list(folder_path, access_token)

            for file in files:
                file_name = file.get("name", "")

                # If it's a folder and we're searching recursively
                if "folder" in file and recursive:
                    subfolder_path = f"{folder_path}/{file_name}" if folder_path else file_name
                    subfolder_results = search_folder_recursive(subfolder_path, file.get("id"))
                    matching_files.extend(subfolder_results)
                    continue

                # Skip folders when looking for files
                if "folder" in file:
                    continue

                # Apply search term filter
                if search_term and search_term.lower() not in file_name.lower():
                    continue

                # Apply file extension filter
                if file_extension and not file_name.lower().endswith(file_extension.lower()):
                    continue

                # Add relevant file metadata
                matching_files.append({
                    "name": file_name,
                    "id": file.get("id"),
                    "size": file.get("size"),
                    "created_datetime": file.get("createdDateTime"),
                    "modified_datetime": file.get("lastModifiedDateTime"),
                    "download_url": file.get("@microsoft.graph.downloadUrl"),
                    "web_url": file.get("webUrl"),
                    "path": f"{folder_path}/{file_name}"
                })

        except Exception as e:
            logger.error(f"Error searching folder {folder_path}: {str(e)}")
            # Continue searching other folders even if one fails

        return matching_files

    try:
        matching_files = search_folder_recursive(path)

        logger.info(f"Found {len(matching_files)} matching files in path: {path} (recursive: {recursive})")
        return matching_files

    except Exception as e:
        logger.error(f"Error searching files in path {path}: {str(e)}")
        raise Exception(f"Error searching files in path {path}: {str(e)}")
