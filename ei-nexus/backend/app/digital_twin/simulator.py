import random


class DigitalTwin:

    def __init__(self):
        self.temperature = 35.0
        self.vibration = 2.0
        self.load = 55.0
        self.rpm = 1450
        self.pressure = 3.2
        self.voltage = 415
        self.current = 18

    def get_state(self):

        self.temperature += random.uniform(-0.3, 0.3)
        self.vibration += random.uniform(-0.1, 0.1)
        self.load += random.uniform(-1.0, 1.0)

        return {
            "temperature": round(self.temperature, 2),
            "vibration": round(self.vibration, 2),
            "load": round(self.load, 2),
            "rpm": self.rpm,
            "pressure": self.pressure,
            "voltage": self.voltage,
            "current": self.current,
        }


digital_twin = DigitalTwin()