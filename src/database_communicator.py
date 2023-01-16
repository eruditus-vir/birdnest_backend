import datetime

from sqlalchemy import create_engine
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, Session
from src.data_parser import DroneInformation, ViolatedPilotInformation
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy import delete, update, select
from typing import List, Tuple, Optional
from src.utils import distance_from_location
from src.constants import CENTER_Y, CENTER_X
import logging

Base = declarative_base()


class ViolatedPilots(Base):
    __tablename__ = "violated_pilots"
    pilot_id = sa.Column(sa.VARCHAR, primary_key=True, index=True)
    first_name = sa.Column(sa.VARCHAR)
    last_name = sa.Column(sa.VARCHAR)
    phone_number = sa.Column(sa.VARCHAR)
    email = sa.Column(sa.VARCHAR)
    created_dt = sa.Column(sa.DATETIME)
    last_violation_at = sa.Column(sa.DATETIME, index=True)
    last_violation_x = sa.Column(sa.FLOAT)
    last_violation_y = sa.Column(sa.FLOAT)
    nearest_violation_x = sa.Column(sa.FLOAT)
    nearest_violation_y = sa.Column(sa.FLOAT)
    # this relationship means that once violated pilots is deleted, foreign key in drone should be set to NULL
    drone = relationship("Drones")

    def to_dict(self):
        return {
            'pilot_id': self.pilot_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone_number': self.phone_number,
            'email': self.email,
            'created_dt': self.created_dt,
            'last_violation_at': self.last_violation_at,
            'last_violation_x': self.last_violation_x,
            'last_violation_y': self.last_violation_y,
            'nearest_violation_x': self.nearest_violation_x,
            'nearest_violation_y': self.nearest_violation_y
        }

    @classmethod
    def from_violated_pilots(cls,
                             pi: ViolatedPilotInformation,
                             position_flown_x: float,
                             position_flown_y: float) -> 'ViolatedPilots':
        return ViolatedPilots(
            pilot_id=pi.pilot_id,
            first_name=pi.first_name,
            last_name=pi.last_name,
            phone_number=pi.phone_number,
            email=pi.email,
            created_dt=pi.created_dt,
            last_violation_at=datetime.datetime.now(),
            last_violation_x=position_flown_x,
            last_violation_y=position_flown_y,
            nearest_violation_x=position_flown_x,  # this is used for comparison at the update stage later
            nearest_violation_y=position_flown_y
        )


class Drones(Base):
    __tablename__ = "drones"
    serial_number = sa.Column(sa.VARCHAR, primary_key=True)
    manufacturer = sa.Column(sa.VARCHAR)
    mac = sa.Column(sa.VARCHAR)
    ipv4 = sa.Column(sa.VARCHAR)
    ipv6 = sa.Column(sa.VARCHAR)
    firmware = sa.Column(sa.VARCHAR)
    position_x = sa.Column(sa.FLOAT)
    position_y = sa.Column(sa.FLOAT)
    altitude = sa.Column(sa.FLOAT)
    is_violating_ndz = sa.Column(sa.BOOLEAN)
    violated_pilot_id = sa.Column(sa.INTEGER, ForeignKey("violated_pilots.pilot_id"),
                                  unique=True, index=True, nullable=True)
    created_at = sa.Column(sa.DATETIME)
    updated_at = sa.Column(sa.DATETIME, index=True)
    # this relationship basically delete associated pilot once drone is deleted
    violated_pilot = relationship("ViolatedPilots", cascade="all, delete")

    def to_dict(self):
        return {
            'serial_number': self.serial_number,
            'manufacturer': self.manufacturer,
            'mac': self.mac,
            'ipv4': self.ipv4,
            'ipv6': self.ipv6,
            'firmware': self.firmware,
            'position_x': self.position_x,
            'position_y': self.position_y,
            'altitude': self.altitude,
            'is_violating_ndz': self.is_violating_ndz,
            'violated_pilot_id': self.violated_pilot_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @classmethod
    def from_drone_information(cls, di: DroneInformation) -> Tuple['Drones', Optional[ViolatedPilots]]:
        pilot = None
        if di.violated_ndz:
            pilot = ViolatedPilots.from_violated_pilots(di.pilot_information,
                                                        di.position_x,
                                                        di.position_y)
        return (Drones(serial_number=di.serial_number,
                       manufacturer=di.manufacturer,
                       mac=di.mac,
                       ipv4=di.ipv4,
                       ipv6=di.ipv6,
                       firmware=di.firmware,
                       position_x=di.position_x,
                       position_y=di.position_y,
                       altitude=di.altitude,
                       is_violating_ndz=di.violated_ndz,
                       created_at=datetime.datetime.now(),
                       updated_at=datetime.datetime.now(),
                       violated_pilot_id=pilot.pilot_id if pilot is not None else None
                       ), pilot)


class DBCom:
    def __init__(self,
                 connection_url: str):
        self.engine = create_engine(connection_url,
                                    isolation_level='SERIALIZABLE')
        # metadata = MetaData(self.engine)
        # metadata.create_all()

    def upsert_drones_and_violated_pilots(self,
                                          drones: List[Drones]):
        all_drones, all_violated_pilot = tuple(zip(*[Drones.from_drone_information(di) for di in drones]))
        all_drones: List[Drones] = list(all_drones)
        logging.info("Received the following drones: {}".format(all_drones))
        all_violated_pilot: List[ViolatedPilots] = [p for p in all_violated_pilot if p is not None]
        session = Session(self.engine)
        # first upsert pilots so that all foreign keys of drones are present
        # upsert drones ensure that on conflict do not update violated_pilot_id
        # this is because we want to keep violated pilot there if they recent violated the zone
        if len(all_drones) > 0:
            for d in all_drones:
                stmt2 = postgresql_insert(Drones).values(d.to_dict())
                # exclude pilot because we handle that later in delete violated pilot
                update_dict = dict(updated_at=d.updated_at, position_x=d.position_x, position_y=d.position_y,
                                   altitude=d.altitude, is_violating_ndz=d.is_violating_ndz)
                if d.violated_pilot_id is not None:
                    update_dict = dict(violated_pilot_id=d.violated_pilot_id)
                stmt2 = stmt2.on_conflict_do_update(index_elements=[Drones.serial_number],
                                                    set_=update_dict)
                session.execute(stmt2)
                session.commit()
        logging.info("Received the following pilots: {}".format(all_violated_pilot))
        if len(all_violated_pilot) > 0:
            # TODO: maybe find a way to make this faster but considering the few data points per update this is fine.
            # it's good thing we use our own DB and not RDS because write is going to cost ALOT.
            # ideal soln: write your own sql statement for this upsert but I lack time
            for vp in all_violated_pilot:
                stmt1 = postgresql_insert(ViolatedPilots).values(vp.to_dict())
                update_dict = dict(
                    last_violation_at=vp.last_violation_at,
                    last_violation_x=vp.last_violation_x,
                    last_violation_y=vp.last_violation_y,
                )

                # following block of code is for update nearest violation locations
                logging.info("checking piklot in db")

                pilot_in_db = session.execute(
                    select(ViolatedPilots).where(ViolatedPilots.pilot_id == vp.pilot_id)).first()
                session.commit()
                logging.info(pilot_in_db)
                if pilot_in_db is not None:
                    pilot_in_db = pilot_in_db["ViolatedPilots"]  # needed to unpack
                    logging.info("comparing {}".format(pilot_in_db))
                    # logging.info(pilot_in_db.to_dict())
                    existing_distance = distance_from_location(pilot_in_db.nearest_violation_x,
                                                               pilot_in_db.nearest_violation_y,
                                                               CENTER_X,
                                                               CENTER_Y)
                    logging.info('existing distance {}'.format(existing_distance))
                    new_distance = distance_from_location(vp.nearest_violation_x,
                                                          vp.nearest_violation_y,
                                                          CENTER_X,
                                                          CENTER_Y)
                    logging.info('new distance {}'.format(new_distance))
                    if new_distance < existing_distance:  # new distance is less, so nearer
                        update_dict['nearest_violation_x'] = vp.nearest_violation_x
                        update_dict['nearest_violation_y'] = vp.nearest_violation_y
                logging.info('update pilot')
                stmt1 = stmt1.on_conflict_do_update(
                    index_elements=[ViolatedPilots.pilot_id],
                    set_=update_dict)
                session.execute(stmt1)
                session.commit()

        session.close()

    def delete_violated_pilot(self):
        """
        we should be deleting pilots whose last violation is more than 10 minutes because it is no longer recent.
        note: we do not cascade back to the drone because the drone can still be within the vicinity.
        However, drone.violated_pilot_id should be set to NULL which is defined in the relationship of
        ViolatedPilots
        :return:
        """
        current_time = datetime.datetime.now()
        ten_minutes_ago = (current_time - datetime.timedelta(minutes=10))
        session = Session(self.engine)
        # associated foreign key in drone should become null
        results = session.execute(
            delete(ViolatedPilots).where(ViolatedPilots.last_violation_at < ten_minutes_ago).returning(
                ViolatedPilots.pilot_id
            )).fetchall()
        session.commit()
        # update to null
        for r in results:
            session.execute(
                update(Drones).where(Drones.violated_pilot_id == r['pilot_id']).values(violated_pilot_id=None))
            session.commit()
        session.close()

    def delete_drones(self):
        """
        Simply delete drones that has not appeared for more than 10 minutes, cascade to the violated pilots too.
        :return:
        """
        current_time = datetime.datetime.now()
        ten_minutes_ago = (current_time - datetime.timedelta(minutes=10))
        session = Session(self.engine)
        session.execute(delete(Drones).where(Drones.updated_at < ten_minutes_ago))
        session.commit()
        session.close()
