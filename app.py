from src.data_fetcher import DataFetcher, BadResponseFromUrlException
from src.database_communicator import DBCom
import time
import os
import logging
import json

logging.getLogger().setLevel(logging.WARNING)

config_f = open('./config/secret.json')
DBCONFIG = json.load(config_f)
# os.getenv('DATABASE_URL').replace("postgres://", "postgresql+psycopg2://")
# TODO: maybe make port changeable
DBURL = "postgresql+psycopg2://{}:{}@postgres/{}".format(DBCONFIG['POSTGRES_USER'],
                                                         DBCONFIG['POSTGRES_PASSWORD'],
                                                         DBCONFIG['POSTGRES_DB'])
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
