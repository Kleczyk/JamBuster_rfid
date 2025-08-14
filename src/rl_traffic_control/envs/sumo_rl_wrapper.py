"""SUMO-RL environment wrapper with additional utilities."""

from typing import Dict, Any, Optional, Tuple
import gymnasium as gym
import numpy as np
import sumo_rl


class SumoRLWrapper:
    """Wrapper for sumo-rl environments with additional utilities."""
    
    @staticmethod
    def create_single_agent_env(env_config: Dict[str, Any]) -> gym.Env:
        """Create single-agent sumo-rl environment.
        
        Args:
            env_config: Environment configuration dict
            
        Returns:
            Single-agent sumo-rl environment
        """
        return sumo_rl.env(
            net_file=env_config.get("net_file", "sumo/single_intersection.net.xml"),
            route_file=env_config.get("route_file", "sumo/single_intersection.rou.xml"),
            use_gui=env_config.get("use_gui", False),
            num_seconds=env_config.get("num_seconds", 3600),
            delta_time=env_config.get("delta_time", 5),
            yellow_time=env_config.get("yellow_time", 4),
            min_green=env_config.get("min_green", 5),
            max_green=env_config.get("max_green", 50),
            sumo_seed=env_config.get("seed", 42),
            reward_fn=env_config.get("reward_fn", "diff-waiting-time"),
            observation_class=env_config.get("observation_class", sumo_rl.ObservationFunction),
            add_system_info=env_config.get("add_system_info", True),
            add_per_agent_info=env_config.get("add_per_agent_info", True),
        )
    
    @staticmethod
    def create_parallel_env(env_config: Dict[str, Any]) -> Any:
        """Create multi-agent parallel sumo-rl environment.
        
        Args:
            env_config: Environment configuration dict
            
        Returns:
            Multi-agent parallel sumo-rl environment
        """
        return sumo_rl.parallel_env(
            net_file=env_config.get("net_file", "sumo/single_intersection.net.xml"),
            route_file=env_config.get("route_file", "sumo/single_intersection.rou.xml"),
            use_gui=env_config.get("use_gui", False),
            num_seconds=env_config.get("num_seconds", 3600),
            delta_time=env_config.get("delta_time", 5),
            yellow_time=env_config.get("yellow_time", 4),
            min_green=env_config.get("min_green", 5),
            max_green=env_config.get("max_green", 50),
            sumo_seed=env_config.get("seed", 42),
            reward_fn=env_config.get("reward_fn", "diff-waiting-time"),
            observation_class=env_config.get("observation_class", sumo_rl.ObservationFunction),
            add_system_info=env_config.get("add_system_info", True),
            add_per_agent_info=env_config.get("add_per_agent_info", True),
        )
    
    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """Get default environment configuration.
        
        Returns:
            Default configuration dict
        """
        return {
            "net_file": "sumo/single_intersection.net.xml",
            "route_file": "sumo/single_intersection.rou.xml",
            "use_gui": False,
            "num_seconds": 3600,
            "delta_time": 5,
            "yellow_time": 4,
            "min_green": 5,
            "max_green": 50,
            "seed": 42,
            "reward_fn": "diff-waiting-time",
            "add_system_info": True,
            "add_per_agent_info": True,
        }
    
    @staticmethod
    def get_available_reward_functions() -> Dict[str, str]:
        """Get available reward functions.
        
        Returns:
            Dict mapping reward function names to descriptions
        """
        return {
            "diff-waiting-time": "Negative difference in cumulative waiting time",
            "average-speed": "Average speed of all vehicles",
            "queue": "Negative total queue length across all intersections",
            "pressure": "Negative pressure (difference between incoming and outgoing vehicles)",
        }
    
    @staticmethod
    def validate_files(net_file: str, route_file: str) -> Tuple[bool, str]:
        """Validate SUMO network and route files exist.
        
        Args:
            net_file: Path to network file
            route_file: Path to route file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        import os
        
        if not os.path.exists(net_file):
            return False, f"Network file not found: {net_file}"
        
        if not os.path.exists(route_file):
            return False, f"Route file not found: {route_file}"
            
        return True, "Files valid"


def create_env(env_config: Dict[str, Any]) -> gym.Env:
    """Environment creator function for Ray RLlib registration.
    
    Args:
        env_config: Environment configuration dict
        
    Returns:
        sumo-rl environment instance
    """
    import sumo_rl
    
    return sumo_rl.env(
        net_file=env_config.get("net_file", "sumo/single_intersection.net.xml"),
        route_file=env_config.get("route_file", "sumo/single_intersection.rou.xml"),
        use_gui=env_config.get("use_gui", False),
        num_seconds=env_config.get("num_seconds", 3600),
        delta_time=env_config.get("delta_time", 5),
        yellow_time=env_config.get("yellow_time", 4),
        min_green=env_config.get("min_green", 5),
        max_green=env_config.get("max_green", 50),
        sumo_seed=env_config.get("seed", 42),
        reward_fn=env_config.get("reward_fn", "diff-waiting-time"),
        observation_class=env_config.get("observation_class", sumo_rl.ObservationFunction),
        add_system_info=env_config.get("add_system_info", True),
        add_per_agent_info=env_config.get("add_per_agent_info", True),
    )