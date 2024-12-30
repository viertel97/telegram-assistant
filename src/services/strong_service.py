import os

import pymysql
from loguru import logger
from quarter_lib_old.database import close_server_connection, create_server_connection

logger.add(
	os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
	format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
	backtrace=True,
	diagnose=True,
)


def update_strong_entries(records, unique_sessions):
	logger.info("start update_strong_entries")
	connection = create_server_connection()
	sql = """
        INSERT INTO `strong` (
            `Date`, `Distance`, `Distance Unit`, `Exercise Name`, `Notes`, `RPE`,
            `Reps`, `Seconds`, `Set Order`, `Weight`, `Weight Unit`,
            `Workout Duration`, `Workout Name`, `Workout Notes`
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
	try:
		with connection.cursor() as cursor:
			cursor.execute("TRUNCATE TABLE strong")
			cursor.execute("ALTER TABLE strong AUTO_INCREMENT = 1")
			connection.commit()
			cursor.executemany(sql, records)
			connection.commit()
	except pymysql.err.IntegrityError as e:
		logger.error(f"IntegrityError: {e}")
	finally:
		close_server_connection(connection)
	done_message = f"truncated table and added {unique_sessions} individual sessions with {len(records)} records in total"
	logger.info(done_message)
	logger.info("stop update_strong_entries")
	return done_message
