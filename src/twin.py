"""
twin.py - Digital Twin: Simulates an industrial motor controller system
Generates realistic sensor data for Temperature, Vibration, Load
"""
import numpy as np
import time
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum


class SystemState(Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    FIXED = "FIXED"


@dataclass
class SensorReading:
    timestamp: float
    temperature: float   # Celsius
    vibration: float     # mm/s RMS
    load: float          # % of rated
    voltage: float       # V DC bus
    current: float       # A
    fan_speed: float     # RPM
    state: str = "NORMAL"


class DigitalTwin:
    """
    Simulates an industrial motor controller with realistic sensor behavior.
    Supports normal operation, injected faults, and post-fix stabilization.
    """

    # Operating thresholds
    THRESHOLDS = {
        "temperature": {"warning": 75.0, "critical": 88.0, "max": 100.0},
        "vibration":   {"warning": 3.5,  "critical": 6.0,  "max": 10.0},
        "load":        {"warning": 80.0, "critical": 92.0, "max": 100.0},
        "voltage":     {"warning": 380.0,"critical": 360.0,"min": 350.0},
    }

    # Normal operating baseline
    BASELINE = {
        "temperature": 55.0,
        "vibration": 1.8,
        "load": 65.0,
        "voltage": 400.0,
        "current": 32.0,
        "fan_speed": 1400.0,
    }

    def __init__(self):
        self.history: List[SensorReading] = []
        self.current = self._baseline_reading()
        self.fault_mode: str = None   # "temperature" | "vibration" | "load" | None
        self.fault_intensity: float = 0.0
        self.is_fixed: bool = False
        self._tick = 0

    def _baseline_reading(self) -> SensorReading:
        """Generate a healthy baseline reading with small noise."""
        return SensorReading(
            timestamp=time.time(),
            temperature=self.BASELINE["temperature"] + np.random.normal(0, 0.8),
            vibration=self.BASELINE["vibration"] + np.random.normal(0, 0.1),
            load=self.BASELINE["load"] + np.random.normal(0, 1.0),
            voltage=self.BASELINE["voltage"] + np.random.normal(0, 1.5),
            current=self.BASELINE["current"] + np.random.normal(0, 0.5),
            fan_speed=self.BASELINE["fan_speed"] + np.random.normal(0, 20),
            state="NORMAL"
        )

    def inject_fault(self, fault_type: str):
        """Inject a specific fault to demonstrate anomaly detection."""
        self.fault_mode = fault_type
        self.fault_intensity = 0.0
        self.is_fixed = False

    def apply_fix(self, fix_type: str) -> Dict:
        """Apply corrective action and begin stabilization."""
        self.is_fixed = True
        self.fault_intensity = max(0, self.fault_intensity - 0.3)
        actions = {
            "cool": {
                "action": "Increased fan PWM duty cycle by 15%, activated secondary cooling loop",
                "expected": "Temperature reduction of 12-18°C over 60 seconds"
            },
            "reduce_vibration": {
                "action": "Applied dynamic balancing correction, reduced motor speed by 8%",
                "expected": "Vibration reduction to below 2.5 mm/s within 30 seconds"
            },
            "reduce_load": {
                "action": "Load shedding initiated, non-critical processes deferred",
                "expected": "Load reduction to 70% within 15 seconds"
            }
        }
        return actions.get(fix_type, {"action": "Generic fix applied", "expected": "System stabilizing"})

    def reset(self):
        """Reset to normal healthy state."""
        self.fault_mode = None
        self.fault_intensity = 0.0
        self.is_fixed = False
        self.history = []
        self._tick = 0
        self.current = self._baseline_reading()

    def tick(self) -> SensorReading:
        """Advance simulation by one time step and return new reading."""
        self._tick += 1

        temp = self.BASELINE["temperature"]
        vib = self.BASELINE["vibration"]
        load = self.BASELINE["load"]
        voltage = self.BASELINE["voltage"]
        current = self.BASELINE["current"]
        fan_speed = self.BASELINE["fan_speed"]

        if self.fault_mode and not self.is_fixed:
            # Ramp up fault intensity gradually (realistic degradation)
            self.fault_intensity = min(1.0, self.fault_intensity + 0.08)
            fi = self.fault_intensity

            if self.fault_mode == "temperature":
                temp += 38 * fi + np.random.normal(0, 1.5)
                fan_speed -= 200 * fi
                current += 8 * fi

            elif self.fault_mode == "vibration":
                vib += 5.5 * fi + np.random.normal(0, 0.3)
                temp += 10 * fi
                current += 4 * fi

            elif self.fault_mode == "load":
                load += 30 * fi + np.random.normal(0, 2.0)
                temp += 15 * fi
                current += 15 * fi
                voltage -= 30 * fi

        elif self.is_fixed:
            # Gradual recovery after fix
            self.fault_intensity = max(0, self.fault_intensity - 0.12)
            fi = self.fault_intensity * 0.3  # recovering

            if self.fault_mode == "temperature":
                temp += 10 * fi
            elif self.fault_mode == "vibration":
                vib += 1.0 * fi
            elif self.fault_mode == "load":
                load += 5 * fi

        # Add realistic sensor noise
        reading = SensorReading(
            timestamp=time.time(),
            temperature=round(temp + np.random.normal(0, 0.5), 2),
            vibration=round(max(0.1, vib + np.random.normal(0, 0.08)), 2),
            load=round(min(100, max(0, load + np.random.normal(0, 1.0))), 2),
            voltage=round(voltage + np.random.normal(0, 1.0), 2),
            current=round(max(0, current + np.random.normal(0, 0.3)), 2),
            fan_speed=round(max(0, fan_speed + np.random.normal(0, 15)), 0),
        )

        # Determine state
        if (reading.temperature >= self.THRESHOLDS["temperature"]["critical"] or
            reading.vibration >= self.THRESHOLDS["vibration"]["critical"] or
            reading.load >= self.THRESHOLDS["load"]["critical"]):
            reading.state = "CRITICAL"
        elif (reading.temperature >= self.THRESHOLDS["temperature"]["warning"] or
              reading.vibration >= self.THRESHOLDS["vibration"]["warning"] or
              reading.load >= self.THRESHOLDS["load"]["warning"]):
            reading.state = "WARNING"
        elif self.is_fixed and self.fault_intensity < 0.1:
            reading.state = "FIXED"
        else:
            reading.state = "NORMAL"

        self.current = reading
        self.history.append(reading)

        # Keep only last 100 readings
        if len(self.history) > 100:
            self.history = self.history[-100:]

        return reading

    def get_history_df(self):
        """Return history as list of dicts for DataFrame conversion."""
        return [
            {
                "time": i,
                "temperature": r.temperature,
                "vibration": r.vibration,
                "load": r.load,
                "voltage": r.voltage,
                "current": r.current,
                "fan_speed": r.fan_speed,
                "state": r.state,
            }
            for i, r in enumerate(self.history)
        ]
