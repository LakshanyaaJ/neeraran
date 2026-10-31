"""
AquaGuard AI - Database Models & Persistence Layer
SQLAlchemy ORM models for Sensor Registry, SensorReadings, and SensorAlerts.
Uses local SQLite database: aquaguard_sensor_health.db
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import datetime
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aquaguard_sensor_health.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class SensorModel(Base):
    __tablename__ = "sensors"

    sensor_id = Column(String(50), primary_key=True, index=True)
    meter_id = Column(String(20), unique=True, index=True, nullable=False)
    campus_id = Column(String(50), default="CAMPUS_01")
    zone_id = Column(String(50), nullable=False)
    sensor_type = Column(String(50), default="FLOW_PRESSURE_METER")
    power_status = Column(String(20), default="ON")                     # ON, OFF
    connectivity_status = Column(String(20), default="CONNECTED")       # CONNECTED, DISCONNECTED
    health_status = Column(String(20), default="HEALTHY")               # HEALTHY, WARNING, FAULTY, OFFLINE, MAINTENANCE
    battery_percentage = Column(Float, default=100.0)
    last_reading_timestamp = Column(DateTime, nullable=True)
    installation_date = Column(DateTime, default=datetime.datetime(2026, 1, 15))
    maintenance_status = Column(String(50), default="OPERATIONAL")      # OPERATIONAL, UNDER_MAINTENANCE

    readings = relationship("SensorReadingModel", back_populates="sensor", cascade="all, delete-orphan")
    alerts = relationship("SensorAlertModel", back_populates="sensor", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'sensor_id': self.sensor_id,
            'meter_id': self.meter_id,
            'campus_id': self.campus_id,
            'zone_id': self.zone_id,
            'sensor_type': self.sensor_type,
            'power_status': self.power_status,
            'connectivity_status': self.connectivity_status,
            'health_status': self.health_status,
            'battery_percentage': round(self.battery_percentage, 1),
            'last_reading_timestamp': self.last_reading_timestamp.isoformat() if self.last_reading_timestamp else None,
            'installation_date': self.installation_date.isoformat() if self.installation_date else None,
            'maintenance_status': self.maintenance_status
        }


class SensorReadingModel(Base):
    __tablename__ = "sensor_readings"

    reading_id = Column(String(50), primary_key=True, index=True)
    sensor_id = Column(String(50), ForeignKey("sensors.sensor_id"), index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    measured_flow_lpm = Column(Float, nullable=True)
    measured_pressure_bar = Column(Float, nullable=True)
    unit_flow = Column(String(20), default="LPM")
    unit_pressure = Column(String(20), default="bar")
    reading_status = Column(String(20), default="RECEIVED")             # RECEIVED, MISSING, CORRUPTED
    is_valid = Column(Boolean, default=True)

    sensor = relationship("SensorModel", back_populates="readings")

    def to_dict(self):
        return {
            'reading_id': self.reading_id,
            'sensor_id': self.sensor_id,
            'timestamp': self.timestamp.isoformat(),
            'measured_flow_lpm': self.measured_flow_lpm,
            'measured_pressure_bar': self.measured_pressure_bar,
            'unit_flow': self.unit_flow,
            'unit_pressure': self.unit_pressure,
            'reading_status': self.reading_status,
            'is_valid': self.is_valid
        }


class SensorAlertModel(Base):
    __tablename__ = "sensor_alerts"

    alert_id = Column(String(50), primary_key=True, index=True)
    sensor_id = Column(String(50), ForeignKey("sensors.sensor_id"), index=True, nullable=False)
    zone_id = Column(String(50), nullable=False)
    alert_type = Column(String(50), nullable=False)                     # Alert category
    severity = Column(String(20), nullable=False)                       # Warning, Critical, Informational
    message = Column(String(500), nullable=False)
    recommended_action = Column(String(500), nullable=False)
    first_detected_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_detected_at = Column(DateTime, default=datetime.datetime.utcnow)
    missing_duration_minutes = Column(Float, default=0.0)
    alert_status = Column(String(20), default="OPEN", index=True)       # OPEN, ACKNOWLEDGED, RESOLVED
    acknowledged_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    sensor = relationship("SensorModel", back_populates="alerts")

    def to_dict(self):
        return {
            'alert_id': self.alert_id,
            'sensor_id': self.sensor_id,
            'zone_id': self.zone_id,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'message': self.message,
            'recommended_action': self.recommended_action,
            'first_detected_at': self.first_detected_at.isoformat() if self.first_detected_at else None,
            'last_detected_at': self.last_detected_at.isoformat() if self.last_detected_at else None,
            'missing_duration_minutes': self.missing_duration_minutes,
            'alert_status': self.alert_status,
            'acknowledged_by': self.acknowledged_by,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully.")

def seed_sensors():
    init_db()
    session = SessionLocal()
    
    # 12 Meters from project simulation
    meter_zone_map = {
        'M01': 'HOSTEL', 'M02': 'HOSTEL',
        'M03': 'ACADEMIC', 'M04': 'ACADEMIC',
        'M05': 'CANTEEN', 'M06': 'CANTEEN',
        'M07': 'LAB', 'M08': 'LAB',
        'M09': 'LIBRARY', 'M10': 'LIBRARY',
        'M11': 'ADMIN', 'M12': 'ADMIN'
    }

    for mid, zid in meter_zone_map.items():
        existing = session.query(SensorModel).filter_by(meter_id=mid).first()
        if not existing:
            # Meter M04 and M10 configured with planned maintenance capability
            maint_stat = "UNDER_MAINTENANCE" if mid in ['M04'] else "OPERATIONAL"
            h_stat = "MAINTENANCE" if mid in ['M04'] else "HEALTHY"
            p_stat = "OFF" if mid in ['M04'] else "ON"
            c_stat = "DISCONNECTED" if mid in ['M04'] else "CONNECTED"
            
            s = SensorModel(
                sensor_id=f"SENSOR_{mid}",
                meter_id=mid,
                campus_id="CAMPUS_01",
                zone_id=zid,
                sensor_type="FLOW_PRESSURE_METER",
                power_status=p_stat,
                connectivity_status=c_stat,
                health_status=h_stat,
                battery_percentage=98.5 if mid != 'M11' else 18.2, # M11 has low battery
                last_reading_timestamp=datetime.datetime(2026, 9, 28, 23, 50, 0),
                maintenance_status=maint_stat
            )
            session.add(s)

    session.commit()
    session.close()
    print("Seeded 12 campus sensors into SQLite database.")

if __name__ == '__main__':
    seed_sensors()
