from src.data_fetcher import DataFetcher, BadResponseFromUrlException
from src.database_communicator import DBCom
import time
import os
import logging

# TODO: maybe change the DB url to directly become postgresql+psycopg2
DBURL = os.getenv('DATABASE_URL').replace("postgres://", "postgresql+psycopg2://")
dbcom = DBCom(DBURL)


# TODO: Logging and alot of logging
def main():
    while True:
        time.sleep(3)
        try:
            data_fetcher = DataFetcher()
            dbcom.upsert_drones_and_violated_pilots(data_fetcher.drone_collection.drones)
            dbcom.delete_drones()
            dbcom.delete_violated_pilot()
        except BadResponseFromUrlException as e:
            logging.warning("Something went wrong during query")
            logging.warning(e)
        except Exception as e:
            logging.warning("Something went wrong")
            logging.error(e)


if __name__ == '__main__':
    main()
