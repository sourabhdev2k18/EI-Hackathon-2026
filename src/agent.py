"""
agent.py - AI Decision Engine
Detects anomalies using Isolation Forest + rule-based logic
Decides corrective actions with explainable reasoning
"""
import numpy as np
from sklearn.ensemble import IsolationForest
from dataclasses import dataclass
from typing import Optional, List, Dict
import json
import os


@dataclass
class AnomalyResult:
    is_anomaly: bool
    anomaly_score: float
    fault_type: Optional[str]       # "temperature" | "vibration" | "load" | None
    severity: str                   # "NORMAL" | "WARNING" | "CRITICAL"
    recommended_action: Optional[str]
    confidence: float
    reasoning: str


class AIDecisionEngine:
    """
    Hybrid AI engine combining:
    1. Isolation Forest for unsupervised anomaly detection
    2. Rule-based expert system for action decisions
    3. Explainable reasoning generation
    """

    THRESHOLDS = {
        "temperature": {"warning": 75.0, "critical": 88.0},
        "vibration":   {"warning": 3.5,  "critical": 6.0},
        "load":        {"warning": 80.0, "critical": 92.0},
    }

    ACTION_MAP = {
        "temperature": "cool",
        "vibration": "reduce_vibration",
        "load": "reduce_load",
    }

    def __init__(self):
        self.model = IsolationForest(
            n_estimators=100,
            contamination=0.1,
            random_state=42
        )
        self._trained = False
        self._train_on_normal_data()
        self.detection_history: List[AnomalyResult] = []

    def _train_on_normal_data(self):
        """Train Isolation Forest on synthetic normal operating data."""
        np.random.seed(42)
        n = 500
        normal_data = np.column_stack([
            np.random.normal(55, 3, n),    # temperature
            np.random.normal(1.8, 0.2, n), # vibration
            np.random.normal(65, 5, n),    # load
            np.random.normal(400, 2, n),   # voltage
            np.random.normal(32, 1, n),    # current
        ])
        self.model.fit(normal_data)
        self._trained = True

    def detect(self, reading) -> AnomalyResult:
        """
        Analyse a sensor reading and return anomaly detection result
        with action recommendation and human-readable reasoning.
        """
        features = np.array([[
            reading.temperature,
            reading.vibration,
            reading.load,
            reading.voltage,
            reading.current,
        ]])

        # Isolation Forest score (-1 anomaly, 1 normal; score < 0 = anomalous)
        score = float(self.model.score_samples(features)[0])
        is_anomaly_ml = score < -0.05

        # Rule-based detection (expert system)
        fault_type = None
        severity = "NORMAL"
        action = None
        reasons = []
        confidence = 0.5

        # Temperature check
        if reading.temperature >= self.THRESHOLDS["temperature"]["critical"]:
            fault_type = "temperature"
            severity = "CRITICAL"
            action = self.ACTION_MAP["temperature"]
            reasons.append(f"Temperature {reading.temperature:.1f}°C exceeds critical threshold {self.THRESHOLDS['temperature']['critical']}°C")
            confidence = 0.95
        elif reading.temperature >= self.THRESHOLDS["temperature"]["warning"]:
            fault_type = "temperature"
            severity = "WARNING"
            action = self.ACTION_MAP["temperature"]
            reasons.append(f"Temperature {reading.temperature:.1f}°C exceeds warning threshold {self.THRESHOLDS['temperature']['warning']}°C")
            confidence = 0.80

        # Vibration check (higher priority if more severe)
        if reading.vibration >= self.THRESHOLDS["vibration"]["critical"]:
            if severity != "CRITICAL":
                fault_type = "vibration"
                severity = "CRITICAL"
                action = self.ACTION_MAP["vibration"]
                confidence = 0.93
            reasons.append(f"Vibration {reading.vibration:.2f} mm/s exceeds critical threshold {self.THRESHOLDS['vibration']['critical']} mm/s")
        elif reading.vibration >= self.THRESHOLDS["vibration"]["warning"]:
            if severity == "NORMAL":
                fault_type = "vibration"
                severity = "WARNING"
                action = self.ACTION_MAP["vibration"]
                confidence = 0.78
            reasons.append(f"Vibration {reading.vibration:.2f} mm/s exceeds warning threshold {self.THRESHOLDS['vibration']['warning']} mm/s")

        # Load check
        if reading.load >= self.THRESHOLDS["load"]["critical"]:
            if severity != "CRITICAL":
                fault_type = "load"
                severity = "CRITICAL"
                action = self.ACTION_MAP["load"]
                confidence = 0.91
            reasons.append(f"Load {reading.load:.1f}% exceeds critical threshold {self.THRESHOLDS['load']['critical']}%")
        elif reading.load >= self.THRESHOLDS["load"]["warning"]:
            if severity == "NORMAL":
                fault_type = "load"
                severity = "WARNING"
                action = self.ACTION_MAP["load"]
                confidence = 0.76
            reasons.append(f"Load {reading.load:.1f}% exceeds warning threshold {self.THRESHOLDS['load']['warning']}%")

        # Combine ML score with rule-based
        is_anomaly = is_anomaly_ml or (severity in ["WARNING", "CRITICAL"])

        if not reasons:
            reasoning = (
                f"All parameters within normal operating range. "
                f"ML anomaly score: {score:.3f} (threshold: -0.05). "
                f"Temperature: {reading.temperature:.1f}°C, "
                f"Vibration: {reading.vibration:.2f} mm/s, "
                f"Load: {reading.load:.1f}%."
            )
            confidence = max(0.3, 1 + score)  # higher score = more normal
        else:
            reasoning = " | ".join(reasons)
            if is_anomaly_ml:
                reasoning += f" | ML model confirms anomaly (score: {score:.3f})"

        result = AnomalyResult(
            is_anomaly=is_anomaly,
            anomaly_score=score,
            fault_type=fault_type,
            severity=severity,
            recommended_action=action,
            confidence=min(0.99, confidence),
            reasoning=reasoning,
        )

        self.detection_history.append(result)
        return result

    def get_detection_stats(self) -> Dict:
        """Return detection statistics for dashboard metrics."""
        if not self.detection_history:
            return {"total": 0, "anomalies": 0, "critical": 0}
        total = len(self.detection_history)
        anomalies = sum(1 for r in self.detection_history if r.is_anomaly)
        critical = sum(1 for r in self.detection_history if r.severity == "CRITICAL")
        return {
            "total": total,
            "anomalies": anomalies,
            "critical": critical,
            "anomaly_rate": round(anomalies / total * 100, 1) if total > 0 else 0,
        }
