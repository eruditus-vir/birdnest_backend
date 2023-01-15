import datetime
from xml.etree import ElementTree as ET
from dateutil import parser
from typing import List, Optional
from src.constants import CENTER_X, CENTER_Y, RADIUS


class ViolatedPilotInformation:
    def __init__(self,
                 pilot_id: str,
                 first_name: str,
                 last_name: str,
                 phone_number: str,
                 created_dt: datetime.datetime,
                 email: str):
        self.pilot_id = pilot_id
        self.first_name = first_name
        self.last_name = last_name
        self.phone_number = phone_number
        self.created_dt = created_dt
        self.email = email

    @classmethod
    def from_dict(cls,
                  data_dict: dict) -> 'ViolatedPilotInformation':
        """
        Example of incoming
        {'pilotId': 'P-7qxuJaBYUa',
         'firstName': 'Roosevelt',
         'lastName': 'Fadel',
         'phoneNumber': '+210499153597',
         'createdDt': '2023-01-11T07:25:09.230Z',
         'email': 'roosevelt.fadel@example.com'}
        :return:
        """
        return ViolatedPilotInformation(
            pilot_id=data_dict['pilotId'],
            first_name=data_dict['firstName'],
            last_name=data_dict['lastName'],
            phone_number=data_dict['phoneNumber'],
            created_dt=parser.parse(data_dict['createdDt']),
            email=data_dict['email']
        )


class DroneInformation:
    def __init__(self,
                 serial_number: str,
                 model: str,
                 manufacturer: str,
                 mac: str,
                 ipv4: str,
                 ipv6: str,
                 firmware: str,
                 position_x: float,
                 position_y: float,
                 altitude: float,
                 snapshot_timestamp: datetime.datetime):
        self.serial_number = serial_number
        self.model = model
        self.manufacturer = manufacturer
        self.mac = mac
        self.ipv4 = ipv4
        self.ipv6 = ipv6
        self.firmware = firmware
        self.position_x = position_x
        self.position_y = position_y
        self.altitude = altitude
        self.snapshot_timestamp = snapshot_timestamp
        self.violated_ndz = self.is_violating_ndz(self.position_x, self.position_y)
        self.pilot_information: Optional[ViolatedPilotInformation] = None

    def set_pilot_information(self, pilot: ViolatedPilotInformation):
        self.pilot_information = pilot

    @staticmethod
    def is_violating_ndz(x, y, center_x=CENTER_X, center_y=CENTER_Y, radius=RADIUS):
        """
        static method top verify if the drone is violating the ndz.
        the logic is simple, from origin position 250000, 250000
        if location satisfy (x - center_x)² + (y - center_y)² <= radius²
        we will return True, otherwise False
        500000
        :param x:
        :param y:
        :param center_x:
        :param center_y:
        :param radius:
        :return:
        """
        return (x - center_x) ** 2 + (y - center_y) ** 2 <= radius ** 2

    @classmethod
    def from_xml_node(cls, node: ET.Element, snapshot_timestamp: datetime.datetime) -> 'DroneInformation':
        if node.tag != "drone":
            raise Exception('Invalid Node: Given Node is not drone Node.')
        data = {}
        for child in node:
            data[child.tag] = child.text
        return DroneInformation(
            serial_number=data['serialNumber'],
            model=data['model'],
            manufacturer=data['manufacturer'],
            mac=data['mac'],
            ipv4=data['ipv4'],
            ipv6=data['ipv6'],
            firmware=data['firmware'],
            position_x=float(data['positionX']),
            position_y=float(data['positionY']),
            altitude=float(data['altitude']),
            snapshot_timestamp=snapshot_timestamp
        )


class DroneCollection:
    def __init__(self,
                 drones: List[DroneInformation]):
        self.drones = drones

    @classmethod
    def from_xml_node(cls, node: ET.Element) -> 'DroneCollection':
        if node.tag != "capture":
            raise Exception('Invalid Node: Given Node is not capture Node.')
        data = {'snapshotTimestamp': node.attrib['snapshotTimestamp'],
                'drones': []}
        data['snapshotTimestamp'] = parser.parse(data['snapshotTimestamp'])
        for child in node:
            data['drones'].append(DroneInformation.from_xml_node(child, data['snapshotTimestamp']))
        return DroneCollection(
            drones=data['drones']
        )


class DeviceInformation:
    def __init__(self,
                 device_id: str,
                 listen_range: int,
                 device_started: datetime.datetime,
                 update_interval_ms: int):
        self.device_started = device_started
        self.listen_range = listen_range
        self.device_id = device_id
        self.update_interval_ms = update_interval_ms

    @classmethod
    def from_xml_node(cls, node: ET.Element) -> 'DeviceInformation':
        """
        class method to create Device Information Object from xml element with deviceInformation tag
        :param node: xml etree element with deviceInformation
        :return:
        """
        if node.tag != "deviceInformation":
            raise Exception('Invalid Node: Given Node is not deviceInformation Node.')
        data = {'deviceId': node.attrib['deviceId']}
        for child in node:
            data[child.tag] = child.text
        return DeviceInformation(
            device_id=data['deviceId'],
            listen_range=int(data['listenRange']),
            device_started=parser.parse(data['deviceStarted']),
            update_interval_ms=int(data['updateIntervalMs'])
        )
