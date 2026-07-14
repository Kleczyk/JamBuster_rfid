"""grid_rfid — simulation + dataset generation for lane-level anomaly localization
on a 3x3 signalized grid with RFID detection (SUMO/TraCI).

Pipeline: scenario.py (network + demand + closures) -> runner.py (SUMO episode +
detector readout) -> generate.py (episodes, train/val/test splits, .npz export).
"""
