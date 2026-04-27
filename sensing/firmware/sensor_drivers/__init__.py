"""
sensor_drivers — one driver per supported sensor class.

Every driver inherits from :class:`SensorDriver` (in ``base.py``) and
exposes the same minimal interface:

    driver = MyDriver(channel="surface", mock=True)
    reading = driver.read()           # → dict with timestamp + values
    driver.close()                    # release hardware handles

Mock mode is the default when the underlying hardware library is not
importable. A driver in mock mode logs a single warning the first
time it is constructed; downstream code does not need to special-case
it.
"""

from sensing.firmware.sensor_drivers.base import (
    SensorDriver,
    SensorReading,
    SensorUnavailableError,
)
from sensing.firmware.sensor_drivers.ds18b20 import DS18B20Driver
from sensing.firmware.sensor_drivers.soil_moisture import (
    CapacitiveSoilMoistureDriver,
)
from sensing.firmware.sensor_drivers.ir_sensor import MLX90614Driver
from sensing.firmware.sensor_drivers.motion_acoustic import (
    PIRMotionDriver,
    MicrophoneDriver,
)

__all__ = [
    "SensorDriver",
    "SensorReading",
    "SensorUnavailableError",
    "DS18B20Driver",
    "CapacitiveSoilMoistureDriver",
    "MLX90614Driver",
    "PIRMotionDriver",
    "MicrophoneDriver",
]
