#!/usr/bin/env python3
"""
Simple script to run the 4-way intersection simulation with SUMO.

Usage:
    python run_simulation.py              # Run with GUI
    python run_simulation.py --no-gui     # Run without GUI (faster)
    python run_simulation.py --steps 100  # Run for limited steps
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


def check_sumo_installed():
    """Check if SUMO is installed and accessible."""
    try:
        result = subprocess.run(
            ["sumo", "--version"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            print(f"✓ SUMO found: {result.stdout.split()[0]}")
            return True
    except FileNotFoundError:
        pass
    
    # Check if SUMO_HOME is set
    sumo_home = os.environ.get("SUMO_HOME")
    if sumo_home:
        sumo_bin = Path(sumo_home) / "bin" / "sumo"
        if sumo_bin.exists():
            print(f"✓ SUMO found in SUMO_HOME: {sumo_home}")
            return True
    
    print("✗ SUMO not found!")
    print("\nPlease install SUMO:")
    print("  Ubuntu/Debian: sudo apt-get install sumo sumo-tools sumo-doc")
    print("  Or follow: https://sumo.dlr.de/docs/Installing/index.html")
    print("\nMake sure SUMO_HOME is set:")
    print("  export SUMO_HOME=/usr/share/sumo")
    return False


def run_simulation(gui=True, max_steps=None, verbose=True):
    """Run the SUMO simulation.
    
    Args:
        gui: If True, use sumo-gui; otherwise use sumo (headless)
        max_steps: Maximum number of simulation steps (None = full simulation)
        verbose: Print verbose output
    """
    script_dir = Path(__file__).parent
    config_file = script_dir / "simulation.sumocfg"
    
    if not config_file.exists():
        print(f"✗ Configuration file not found: {config_file}")
        return False
    
    # Build command
    sumo_binary = "sumo-gui" if gui else "sumo"
    cmd = [sumo_binary, "-c", str(config_file)]
    
    if max_steps:
        cmd.extend(["--end", str(max_steps)])
    
    if verbose:
        cmd.append("--verbose")
    
    # Add statistics
    cmd.append("--duration-log.statistics")
    
    print(f"\n{'='*60}")
    print(f"Starting SUMO Simulation")
    print(f"{'='*60}")
    print(f"Binary: {sumo_binary}")
    print(f"Config: {config_file.name}")
    print(f"GUI: {'Yes' if gui else 'No'}")
    if max_steps:
        print(f"Max steps: {max_steps}")
    print(f"{'='*60}\n")
    
    try:
        # Run SUMO
        result = subprocess.run(cmd, cwd=script_dir)
        
        if result.returncode == 0:
            print(f"\n{'='*60}")
            print("✓ Simulation completed successfully!")
            print(f"{'='*60}")
            
            # Check output files
            output_files = [
                "tripinfo.xml",
                "summary.xml",
                "simulation.log"
            ]
            
            print("\nGenerated output files:")
            for fname in output_files:
                fpath = script_dir / fname
                if fpath.exists():
                    size = fpath.stat().st_size
                    print(f"  ✓ {fname} ({size:,} bytes)")
                else:
                    print(f"  ✗ {fname} (not found)")
            
            return True
        else:
            print(f"\n✗ Simulation failed with exit code {result.returncode}")
            return False
            
    except FileNotFoundError:
        print(f"✗ {sumo_binary} not found in PATH")
        print("Make sure SUMO is installed and in your PATH")
        return False
    except KeyboardInterrupt:
        print("\n\n⚠ Simulation interrupted by user")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Run 4-way intersection SUMO simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Run without GUI (faster, for batch processing)"
    )
    
    parser.add_argument(
        "--steps",
        type=int,
        default=None,
        help="Maximum number of simulation steps (default: full 3600s)"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output"
    )
    
    args = parser.parse_args()
    
    # Check SUMO installation
    if not check_sumo_installed():
        return 1
    
    # Run simulation
    success = run_simulation(
        gui=not args.no_gui,
        max_steps=args.steps,
        verbose=not args.quiet
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())








