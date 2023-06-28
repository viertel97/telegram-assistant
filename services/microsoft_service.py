import os

import msal
import requests
from loguru import logger

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)

base_url = "https://graph.microsoft.com/v1.0/"
endpoint = base_url + "me"

AUTHORITY_URL = "https://login.microsoftonline.com/consumers/"

SCOPES = ["User.Read", "Files.Read.All"]
AUTH_CODE = "M.R3_BAY.9f8487fe-43c1-fbed-7e88-244f9f33d43b"

CLIENT_ID = "00a50573-4b12-4227-ae43-de1b40fff7ac"
CLIENT_SECRET = "M~68Q~UCsHU6aQQSBkDm34ihiBLBAnqZHDPa-cHT"

REFRESH_TOKEN = 'M.R3_BAY.-CQsxwHOINJ9KGRTVqVKfryEwoBgPJHgB12uQvHpKKsMyKIrOOa8g1yYMc*D9XWWpvch3HTO*EiA2Y6w0nOWXr5zzCh5rtaglIFlN4he0Y9YUjGMpvfKvG!L9lv!70UYcEqmWc3mqDJnGS2nqU74OOnZ8Lw4op1p*JKlxJdjKJ*X2Qsv2AhKR9WSvN491ZsFqurRUwKjwfD950w6PXUuLK556Tcu4LR3vpeEW4lVTlkEnWGTFLcg28xJMKzjcSqhMWrZEgfGI7KUdCgAvuBwR4nIZw9rnk2KEvFHIl7QBTsNG7Rh31j2KWV1DzsRF6qiZcW1UOqNXWs5mRErZGscw0CXYCZIwcfr82*Dz28BqSAhsn8gr6op4paSXudAXNso!jXRH81uJOkee2OZbxZwDDUA$'

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


def get_file_from_path(path, file_name):
    access_token = get_access_token()
    headers = {'Authorization': 'Bearer ' + access_token}
    url = base_url + "me/drive/root:/" + path
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
