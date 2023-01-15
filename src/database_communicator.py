import datetime

from sqlalchemy import create_engine
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, Session
from data_parser import DroneInformation, ViolatedPilotInformation
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy import delete
from typing import List, Tuple, Optional
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
    # this relationship means that once violated pilots is deleted, foreign key in drone should be set to NULL
    drone = relationship("Drones")

    @classmethod
    def from_violated_pilots(cls, pi: ViolatedPilotInformation) -> 'ViolatedPilots':
        return ViolatedPilots(
            pilot_id=pi.pilot_id,
            first_name=pi.first_name,
            last_name=pi.last_name,
            phone_number=pi.phone_number,
            email=pi.email,
            created_dt=pi.created_dt,
            last_violation_at=datetime.datetime.now().isoformat(),
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
    violated_pilot = relationship("ViolatedPilots", cascade="all, delete-orphan")

    @classmethod
    def from_drone_information(cls, di: DroneInformation) -> Tuple['Drones', Optional[ViolatedPilots]]:
        pilot = None
        if di.pilot_information is not None:
            pilot = ViolatedPilots.from_violated_pilots(di.pilot_information)
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
                       created_at=datetime.datetime.now().isoformat(),
                       updated_at=datetime.datetime.now().isoformat(),
                       violated_pilot_id=pilot
                       ), pilot)


class DBCom:
    def __init__(self,
                 connection_url: str):
        self.engine = create_engine(connection_url,
                                    isolation_level='SERIALIZABLE')

    def upsert_drones_and_violated_pilots(self,
                                          drones: List[Drones]):
        all_drones, all_violated_pilot = tuple(zip(*[Drones.from_drone_information(di) for di in drones]))
        all_drones = list(all_drones)
        logging.info("Received the following drones: {}".format(all_drones))
        logging.info("The following ")
        all_violated_pilot = [p for p in all_violated_pilot if p is not None]
        session = Session(self.engine)
        # first upsert pilots so that all foreign keys of drones are present
        stmt1 = postgresql_insert(ViolatedPilots).values(all_violated_pilot)
        stmt1 = stmt1.on_conflict_do_update(index_elements=[ViolatedPilots.pilot_id])
        session.execute(stmt1)
        session.commit()
        # upsert drones ensure that on conflict do not update violated_pilot_id
        # this is because we want to keep violated pilot there if they recent violated the zone
        stmt2 = postgresql_insert(Drones).values(all_drones)
        # exclude pilot because we handle that later in delete violated pilot
        stmt2 = stmt2.on_conflict_do_update(index_elements=[Drones.serial_number],
                                            set_=dict(created_at=stmt2.excluded.created_at,
                                                      violated_pilot_id=stmt2.excluded.violated_pilot_id))
        session.execute(stmt2)
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
        ten_minutes_ago = (current_time - datetime.timedelta(minutes=10)).isoformat()
        session = Session(self.engine)
        # associated foreign key in drone should become null
        session.execute(delete(ViolatedPilots).where(ViolatedPilots.last_violation_at < ten_minutes_ago))
        session.commit()
        session.close()

    def delete_drones(self):
        """
        Simply delete drones that has not appeared for more than 10 minutes, cascade to the violated pilots too.
        :return:
        """
        current_time = datetime.datetime.now()
        ten_minutes_ago = (current_time - datetime.timedelta(minutes=10)).isoformat()
        session = Session(self.engine)
        session.execute(delete(Drones).where(Drones.updated_at < ten_minutes_ago))
        session.commit()
        session.close()
