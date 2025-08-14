"""SUMO Environment wrapper for Ray RLlib training."""

import os
import sys
from typing import Dict, Optional, Tuple, Any

import gymnasium as gym
import numpy as np
import traci
import sumolib
from gymnasium import spaces
from ray.rllib.env import BaseEnv


class SumoRLlibEnv(gym.Env):
    """SUMO traffic simulation environment for Ray RLlib."""
    
    def __init__(self, env_config: Dict[str, Any]):
        """Initialize SUMO environment with RLlib config.
        
        Args:
            env_config: Environment configuration dict from RLlib
        """
        super().__init__()
        
        # Extract config parameters
        self.sumo_cfg_file = env_config.get("sumo_cfg_file", "sumo/single_intersection.sumocfg")
        self.use_gui = env_config.get("use_gui", False)
        self.max_steps = env_config.get("max_steps", 3600)
        self.step_length = env_config.get("step_length", 1.0)
        self.port = env_config.get("port", 8813)
        self.seed = env_config.get("seed", None)
        
        # Auto-detect SUMO binary
        if self.use_gui:
            self.sumo_binary = sumolib.checkBinary('sumo-gui')
        else:
            self.sumo_binary = sumolib.checkBinary('sumo')
            
        # Simulation state
        self.step_count = 0
        self.connection_label = f"sumo_{self.port}_{id(self)}"
        
        # Define action and observation spaces
        self.action_space = spaces.Discrete(4)  # 4 traffic light phases
        self.observation_space = spaces.Box(
            low=0, high=100, shape=(8,), dtype=np.float32
        )
        
    def reset(self, *, seed: Optional[int] = None, options: Optional[Dict] = None):
        """Reset the environment."""
        super().reset(seed=seed)
        
        if seed is not None:
            self.seed = seed
            
        # Close existing connection
        try:
            if traci.isConnected(self.connection_label):
                traci.close(self.connection_label)
        except:
            pass
            
        # Start SUMO
        sumo_cmd = [
            self.sumo_binary,
            "-c", self.sumo_cfg_file,
            "--step-length", str(self.step_length),
            "--no-step-log",
            "--no-warnings", 
            "--quit-on-end",
            "--start",
            "--remote-port", str(self.port),
        ]
        
        if self.seed is not None:
            sumo_cmd.extend(["--seed", str(self.seed)])
            
        if not self.use_gui:
            sumo_cmd.append("--no-gui")
            
        try:
            traci.start(sumo_cmd, label=self.connection_label)
            traci.switch(self.connection_label)
        except Exception as e:
            # Try different port if connection fails
            self.port += 1
            sumo_cmd[-1] = str(self.port)
            traci.start(sumo_cmd, label=self.connection_label)
            traci.switch(self.connection_label)
        
        self.step_count = 0
        
        # Get initial observation
        obs = self._get_observation()
        info = {"step": self.step_count}
        
        return obs, info
        
    def step(self, action: int):
        """Execute one environment step."""
        # Apply action
        self._apply_action(action)
        
        # Advance simulation
        traci.simulationStep()
        self.step_count += 1
        
        # Get new observation
        obs = self._get_observation()
        
        # Calculate reward
        reward = self._get_reward()
        
        # Check if done
        min_expected = traci.simulation.getMinExpectedNumber()
        terminated = self.step_count >= self.max_steps or min_expected <= 0
        truncated = False
        
        info = {
            "step": self.step_count,
            "vehicles": min_expected
        }
        
        return obs, reward, terminated, truncated, info
        
    def close(self):
        """Close the environment."""
        try:
            if traci.isConnected(self.connection_label):
                traci.close(self.connection_label)
        except:
            pass
            
    def _get_observation(self) -> np.ndarray:
        """Get current observation from SUMO."""
        try:
            tl_ids = traci.trafficlight.getIDList()
            if not tl_ids:
                return np.zeros(8, dtype=np.float32)
                
            tl_id = tl_ids[0]
            controlled_lanes = traci.trafficlight.getControlledLanes(tl_id)
            
            queue_lengths = []
            for lane_id in controlled_lanes[:8]:
                try:
                    queue_length = traci.lane.getLastStepHaltingNumber(lane_id)
                    queue_lengths.append(queue_length)
                except:
                    queue_lengths.append(0)
                    
            # Pad or truncate to fixed size
            queue_lengths = queue_lengths[:8] + [0] * max(0, 8 - len(queue_lengths))
            
            return np.array(queue_lengths, dtype=np.float32)
            
        except Exception:
            return np.zeros(8, dtype=np.float32)
        
    def _apply_action(self, action: int):
        """Apply action to SUMO simulation."""
        try:
            tl_ids = traci.trafficlight.getIDList()
            if not tl_ids:
                return
                
            tl_id = tl_ids[0]
            
            # Map action to traffic light phase
            phase_map = {
                0: "GrGr",  # North-South green
                1: "yryr",  # North-South yellow  
                2: "rGrG",  # East-West green
                3: "ryry",  # East-West yellow
            }
            
            if action in phase_map:
                traci.trafficlight.setRedYellowGreenState(
                    tl_id, phase_map[action]
                )
        except Exception:
            pass
            
    def _get_reward(self) -> float:
        """Calculate reward based on current simulation state."""
        try:
            total_queue = 0
            tl_ids = traci.trafficlight.getIDList()
            
            if tl_ids:
                tl_id = tl_ids[0]
                controlled_lanes = traci.trafficlight.getControlledLanes(tl_id)
                
                for lane_id in controlled_lanes:
                    try:
                        queue_length = traci.lane.getLastStepHaltingNumber(lane_id)
                        total_queue += queue_length
                    except:
                        pass
                        
            return -total_queue  # Minimize waiting
            
        except Exception:
            return 0.0