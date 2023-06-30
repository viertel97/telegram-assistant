import pymysql.cursors
from quarter_lib.akeyless import get_target
from quarter_lib.logging import setup_logging

logger = setup_logging(__file__)
DB_USER_NAME, DB_HOST_NAME, DB_PASSWORD, DB_PORT, DB_NAME = get_target("private")
DB_USER_NAME_MONICA, _, DB_PASSWORD_MONICA, DB_PORT_MONICA, DB_NAME_MONICA = get_target("monica")


def create_server_connection():
    return pymysql.connect(
        host=DB_HOST_NAME,
        port=3306,
        user=DB_USER_NAME,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
    )


def create_monica_server_connection():
    return pymysql.connect(
        host=DB_HOST_NAME,
        port=3306,
        user=DB_USER_NAME_MONICA,
        password=DB_PASSWORD_MONICA,
        database=DB_NAME_MONICA,
        cursorclass=pymysql.cursors.DictCursor,
    )


def close_server_connection(connection):
    connection.close()
