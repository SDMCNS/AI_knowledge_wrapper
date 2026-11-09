# Apollo Flight Envelope & Safety Verification Guidelines

## 1. Emergency Failsafe Trigger Conditions
The autonomous flight supervisory monitor continuously evaluates system telemetry against hard safety constraints. A transition to an emergency recovery state is triggered when any of the following parameters are breached:

1. **Lost Link Timeout**: Absence of valid telemetry heartbeat packets across both primary UHF (915 MHz) and LTE cellular channels for more than **1500 ms**.
2. **Critical Low Battery (Voltage Floor)**: Total battery bus voltage dropping below **18.2 V** under load for greater than 3.0 continuous seconds.
3. **Severe Sensor Divergence**: Innovation residuals between primary and secondary IMU vectors exceeding 3.5 standard deviations for more than 50 consecutive milliseconds.
4. **Attitude Loss-of-Control**: Pitch exceeding ±45 degrees or roll exceeding ±60 degrees without operator stick deflection.

## 2. Geofence Containment Protocols
- **Inclusion Geofence**: All flight trajectories must remain within the pre-cleared polygon.
- **Buffer Zone**: A 50-meter warning perimeter triggers automatic speed restriction to a maximum of 5.0 m/s.
- **Hard Breach Action**: Crossing the physical inclusion perimeter immediately disengages autonomous cruise and executes an emergency Return-to-Home (RTH) path at a minimum altitude of 60 meters above ground level.

## 3. Autonomous Parachute Deployment Envelope
In the event of unrecoverable catastrophic motor or structural failure, the autonomous ballistic parachute is ejected via pyrotechnic initiator under the following conditions:
- Vertical descent rate exceeds **12.0 m/s** downward velocity while barometric altimeter registers altitude > 25 meters AGL.
- Total vehicle inverted roll orientation lasting longer than 400 milliseconds below 100 meters altitude.
