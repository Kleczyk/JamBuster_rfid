#!/usr/bin/env python3
"""Demo script showing how to run SUMO with and without GUI."""

import argparse
import time
import sys
from pathlib import Path

import traci
import sumolib


def run_sumo_simulation(sumo_cfg_file: str, use_gui: bool = False, max_steps: int = 100):
    """Run basic SUMO simulation.
    
    Args:
        sumo_cfg_file: Path to SUMO configuration file
        use_gui: Whether to use SUMO GUI
        max_steps: Maximum simulation steps
    """
    # Auto-detect SUMO binary
    if use_gui:
        sumo_binary = sumolib.checkBinary('sumo-gui')
        print("Starting SUMO with GUI...")
    else:
        sumo_binary = sumolib.checkBinary('sumo')
        print("Starting SUMO in command line mode...")
    
    # Build SUMO command
    sumo_cmd = [
        sumo_binary,
        "-c", sumo_cfg_file,
        "--step-length", "1.0",
        "--start",
        "--quit-on-end",
    ]
    
    if not use_gui:
        sumo_cmd.append("--no-gui")
    
    # Start SUMO
    traci.start(sumo_cmd)
    
    step = 0
    try:
        while step < max_steps and traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            step += 1
            
            # Print simulation info every 10 steps
            if step % 10 == 0:
                vehicle_count = traci.simulation.getMinExpectedNumber()
                print(f"Step {step}: {vehicle_count} vehicles remaining")
                
            # Add delay for GUI visualization
            if use_gui:
                time.sleep(0.1)
                
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user")
    finally:
        traci.close()
        print(f"Simulation ended after {step} steps")


def demo_with_traffic_lights():
    """Demo with traffic light control."""
    print("\n=== Traffic Light Control Demo ===")
    
    # This would need a proper SUMO network file
    print("This demo requires a SUMO network with traffic lights.")
    print("Example traffic light control:")
    
    code = '''
# Get all traffic light IDs
tl_ids = traci.trafficlight.getIDList()
print(f"Traffic lights: {tl_ids}")

# Control first traffic light
if tl_ids:
    tl_id = tl_ids[0]
    
    # Get current phase
    current_phase = traci.trafficlight.getRedYellowGreenState(tl_id)
    print(f"Current phase: {current_phase}")
    
    # Set new phase (example: all red)
    traci.trafficlight.setRedYellowGreenState(tl_id, "rrrr")
    
    # Get controlled lanes
    lanes = traci.trafficlight.getControlledLanes(tl_id)
    print(f"Controlled lanes: {lanes}")
    
    # Get queue lengths
    for lane_id in lanes:
        queue = traci.lane.getLastStepHaltingNumber(lane_id)
        print(f"Lane {lane_id}: {queue} waiting vehicles")
    '''
    
    print(code)


def main():
    """Main demo function."""
    parser = argparse.ArgumentParser(description="SUMO Demo Script")
    parser.add_argument("--config", default="sumo/demo.sumocfg", help="SUMO config file")
    parser.add_argument("--gui", action="store_true", help="Use SUMO GUI")
    parser.add_argument("--steps", type=int, default=100, help="Max simulation steps")
    parser.add_argument("--demo-only", action="store_true", help="Show demo code only")
    
    args = parser.parse_args()
    
    if args.demo_only:
        demo_with_traffic_lights()
        return
    
    # Check if config file exists
    if not Path(args.config).exists():
        print(f"Error: Config file {args.config} not found!")
        print("\nTo run SUMO simulation, you need:")
        print("1. SUMO network file (.net.xml)")
        print("2. SUMO routes file (.rou.xml)")  
        print("3. SUMO configuration file (.sumocfg)")
        print("\nExample commands:")
        print("# With GUI:")
        print("python scripts/run_sumo_demo.py --config sumo/demo.sumocfg --gui")
        print("\n# Without GUI:")
        print("python scripts/run_sumo_demo.py --config sumo/demo.sumocfg")
        return
    
    try:
        run_sumo_simulation(args.config, args.gui, args.steps)
    except Exception as e:
        print(f"Error running simulation: {e}")
        print("\nMake sure SUMO is installed and in your PATH")
        print("Install SUMO: https://eclipse.org/sumo/")


if __name__ == "__main__":
    main()