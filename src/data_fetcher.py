import requests
from src.data_parser import ViolatedPilotInformation, DeviceInformation, DroneInformation, DroneCollection
import urllib.parse as urlparse
from xml.etree import ElementTree as ET
import json
import logging


class BadResponseFromUrlException(Exception):
    """
    Exception raised from errors in any Data Query for this application
    """

    def __init__(self, status_code, url):
        self.status_code = status_code
        self.url = url
        super().__init__("Following URL returned bad status code\nStatus Code: {}\nURL used: {}".format(status_code,
                                                                                                        url))


class DataFetcher:
    def __init__(self,
                 drone_url='https://assignments.reaktor.com/birdnest/drones',
                 pilot_url='https://assignments.reaktor.com/birdnest/pilots/'):
        response = requests.get(drone_url)
        if 200 > response.status_code > 299:
            raise BadResponseFromUrlException(response.status_code, drone_url)
        root = ET.fromstring(response.content)
        parsed_dict = {}
        for child in root:
            if child.tag == 'deviceInformation':
                parsed_dict['deviceInformation'] = DeviceInformation.from_xml_node(child)
            elif child.tag == 'capture':
                parsed_dict['capture'] = DroneCollection.from_xml_node(child)
        self.drone_url = drone_url
        self.device_information = parsed_dict['deviceInformation']
        self.drone_collection = parsed_dict['capture']
        self.violated_pilot_data_fetcher = ViolatedPilotDataFetcher(pilot_url)
        for drone in self.drone_collection.drones:
            if drone.violated_ndz:
                try:
                    pilot = self.violated_pilot_data_fetcher.query_violated_pilot_data(drone)
                    drone.set_pilot_information(pilot)
                except BadResponseFromUrlException as e:
                    logging.warning("Unable to query for following drone {}".format(drone.serial_number))
                    logging.warning(e)
                except Exception as e:
                    logging.warning("Something went wrong during query")
                    logging.warning(e)


class ViolatedPilotDataFetcher:
    def __init__(self, pilot_url='https://assignments.reaktor.com/birdnest/pilots/'):
        self.pilot_url = pilot_url

    def query_violated_pilot_data(self,
                                  drone: DroneInformation) -> ViolatedPilotInformation:
        query_url = self.pilot_url + drone.serial_number
        response = requests.get(urlparse.urlparse(query_url).geturl())  # parse url for cleaning
        if 200 > response.status_code > 299:
            raise BadResponseFromUrlException(response.status_code, self.pilot_url)
        result = json.loads(response.content)
        return ViolatedPilotInformation.from_dict(result)
