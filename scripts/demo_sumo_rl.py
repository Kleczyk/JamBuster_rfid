#!/usr/bin/env python3
"""Demo script showing SUMO-RL environment functionality."""

import argparse
import time
import random
from pathlib import Path

from rl_traffic_control.envs.sumo_rl_wrapper import SumoRLWrapper


def demo_random_agent(env_config: dict, episodes: int = 3):
    """Demonstrate random agent in SUMO-RL environment.
    
    Args:
        env_config: Environment configuration
        episodes: Number of episodes to run
    """
    print("Creating SUMO-RL environment...")
    env = SumoRLWrapper.create_single_agent_env(env_config)
    
    print(f"Environment created successfully!")
    print(f"Action space: {env.action_space}")
    print(f"Observation space: {env.observation_space}")
    print(f"Reward function: {env_config.get('reward_fn', 'default')}")
    print()
    
    # Get available reward functions
    reward_functions = SumoRLWrapper.get_available_reward_functions()
    current_reward = env_config.get('reward_fn', 'diff-waiting-time')
    print(f"Current reward: {reward_functions.get(current_reward, 'Unknown')}")
    print()
    
    total_rewards = []
    total_steps = []
    
    for episode in range(episodes):
        print(f"=== Episode {episode + 1}/{episodes} ===")
        
        # Reset environment
        obs, info = env.reset()
        episode_reward = 0
        step = 0
        
        print(f"Initial observation: {obs}")
        print(f"Initial info: {info}")
        
        # Run episode
        while True:
            # Random action
            action = env.action_space.sample()
            
            # Step environment
            obs, reward, terminated, truncated, info = env.step(action)
            
            episode_reward += reward
            step += 1
            
            # Print progress every 50 steps
            if step % 50 == 0:
                print(f"  Step {step}: Action={action}, Reward={reward:.2f}, Obs={obs[:3]}...")
                
            # Check if episode ended
            if terminated or truncated:
                break
                
            # Early stop for demo (optional)
            if step >= 200:  # Limit for demo purposes
                break
        
        total_rewards.append(episode_reward)
        total_steps.append(step)
        
        print(f"Episode completed:")
        print(f"  Total steps: {step}")
        print(f"  Total reward: {episode_reward:.2f}")
        print(f"  Average reward per step: {episode_reward/step:.3f}")
        print()
    
    env.close()
    
    # Summary statistics
    if total_rewards:
        avg_reward = sum(total_rewards) / len(total_rewards)
        avg_steps = sum(total_steps) / len(total_steps)
        
        print("=" * 50)
        print("DEMO SUMMARY")
        print("=" * 50)
        print(f"Episodes completed: {len(total_rewards)}")
        print(f"Average reward: {avg_reward:.2f}")
        print(f"Average steps: {avg_steps:.1f}")
        print(f"Reward function used: {current_reward}")
        print(f"Description: {reward_functions.get(current_reward, 'Unknown')}")


def demo_environment_info():
    """Demonstrate environment configuration options."""
    print("SUMO-RL Environment Configuration Options:")
    print("=" * 50)
    
    # Show default config
    default_config = SumoRLWrapper.get_default_config()
    print("Default configuration:")
    for key, value in default_config.items():
        print(f"  {key}: {value}")
    
    print()
    
    # Show available reward functions
    print("Available reward functions:")
    reward_functions = SumoRLWrapper.get_available_reward_functions()
    for name, description in reward_functions.items():
        print(f"  {name}: {description}")
    
    print()
    print("Key parameters:")
    print("  - delta_time: Time between RL agent actions (seconds)")
    print("  - yellow_time: Duration of yellow traffic light phase")
    print("  - min_green/max_green: Min/max duration for green phases")
    print("  - num_seconds: Total simulation time")
    print("  - use_gui: Whether to show SUMO GUI visualization")


def main():
    """Main demo function."""
    parser = argparse.ArgumentParser(description="SUMO-RL Environment Demo")
    parser.add_argument("--gui", action="store_true", help="Use SUMO GUI")
    parser.add_argument("--episodes", type=int, default=3, help="Number of episodes")
    parser.add_argument("--net-file", default="sumo/single_intersection.net.xml", help="SUMO network file")
    parser.add_argument("--route-file", default="sumo/single_intersection.rou.xml", help="SUMO route file")
    parser.add_argument("--reward-fn", default="diff-waiting-time", 
                        choices=["diff-waiting-time", "average-speed", "queue", "pressure"],
                        help="Reward function to test")
    parser.add_argument("--delta-time", type=int, default=5, help="Time between actions (seconds)")
    parser.add_argument("--info-only", action="store_true", help="Show environment info only")
    
    args = parser.parse_args()
    
    if args.info_only:
        demo_environment_info()
        return
    
    # Validate files exist
    is_valid, error_msg = SumoRLWrapper.validate_files(args.net_file, args.route_file)
    if not is_valid:
        print(f"Error: {error_msg}")
        print("Please run: python scripts/create_sumo_network.py")
        return
    
    # Environment configuration
    env_config = {
        "net_file": args.net_file,
        "route_file": args.route_file,
        "use_gui": args.gui,
        "num_seconds": 300,  # Shorter for demo
        "delta_time": args.delta_time,
        "yellow_time": 4,
        "min_green": 5,
        "max_green": 30,  # Shorter max for more frequent actions
        "seed": 42,
        "reward_fn": args.reward_fn,
        "add_system_info": True,
        "add_per_agent_info": True,
    }
    
    print(f"Starting SUMO-RL demo with {args.episodes} episodes...")
    print(f"GUI enabled: {args.gui}")
    print(f"Reward function: {args.reward_fn}")
    print(f"Action frequency: every {args.delta_time} seconds")
    print()
    
    try:
        demo_random_agent(env_config, args.episodes)
    except Exception as e:
        print(f"Error during demo: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure SUMO is installed: sumo --version")
        print("2. Create network files: python scripts/create_sumo_network.py")
        print("3. Install sumo-rl: uv sync")


if __name__ == "__main__":
    main()