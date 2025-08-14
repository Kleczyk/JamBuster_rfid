#!/usr/bin/env python3
"""Evaluate trained RLlib agents using sumo-rl."""

import argparse
import os
from pathlib import Path

import ray
from ray.rllib.algorithms import Algorithm
from ray.tune.registry import register_env

from rl_traffic_control.envs.sumo_rl_wrapper import create_env, SumoRLWrapper


def main():
    """Main evaluation function."""
    parser = argparse.ArgumentParser(description="Evaluate RLlib agent with sumo-rl")
    parser.add_argument("--checkpoint", required=True, help="Path to checkpoint")
    parser.add_argument("--algorithm", choices=["PPO", "A3C"], default="PPO", help="Algorithm type")
    parser.add_argument("--gui", action="store_true", help="Use SUMO GUI")
    parser.add_argument("--episodes", type=int, default=10, help="Evaluation episodes")
    parser.add_argument("--net-file", default="sumo/single_intersection.net.xml", help="SUMO network file")
    parser.add_argument("--route-file", default="sumo/single_intersection.rou.xml", help="SUMO route file")
    parser.add_argument("--reward-fn", default="diff-waiting-time", 
                        choices=["diff-waiting-time", "average-speed", "queue", "pressure"],
                        help="Reward function to use")
    parser.add_argument("--delta-time", type=int, default=5, help="Time between actions (seconds)")
    
    args = parser.parse_args()
    
    # Validate files
    is_valid, error_msg = SumoRLWrapper.validate_files(args.net_file, args.route_file)
    if not is_valid:
        print(f"Error: {error_msg}")
        return
    
    # Initialize Ray
    ray.init(ignore_reinit_error=True)
    
    # Register environment
    register_env("sumo_rl_env", create_env)
    
    # Load trained agent
    try:
        agent = Algorithm.from_checkpoint(args.checkpoint)
        print(f"Loaded {args.algorithm} agent from {args.checkpoint}")
    except Exception as e:
        print(f"Error loading checkpoint: {e}")
        return
    
    # Create environment for evaluation
    env_config = {
        "net_file": args.net_file,
        "route_file": args.route_file,
        "use_gui": args.gui,
        "num_seconds": 3600,
        "delta_time": args.delta_time,
        "yellow_time": 4,
        "min_green": 5,
        "max_green": 50,
        "seed": 42,
        "reward_fn": args.reward_fn,
        "add_system_info": True,
        "add_per_agent_info": True,
    }
    
    env = SumoRLWrapper.create_single_agent_env(env_config)
    
    total_rewards = []
    total_steps = []
    
    print(f"Starting evaluation with {args.episodes} episodes...")
    print(f"Reward function: {args.reward_fn}")
    print(f"Delta time: {args.delta_time}s")
    
    for episode in range(args.episodes):
        obs, info = env.reset()
        episode_reward = 0
        step = 0
        
        print(f"\nEpisode {episode + 1}/{args.episodes}")
        
        while True:
            try:
                action = agent.compute_single_action(obs, explore=False)
                obs, reward, terminated, truncated, info = env.step(action)
                
                episode_reward += reward
                step += 1
                
                if step % 100 == 0:
                    print(f"  Step {step}, Current reward: {reward:.2f}")
                
                if terminated or truncated:
                    break
                    
            except Exception as e:
                print(f"Error during episode {episode + 1}: {e}")
                break
                
        total_rewards.append(episode_reward)
        total_steps.append(step)
        print(f"  Completed: {step} steps, Total reward: {episode_reward:.2f}")
        
    env.close()
    
    # Print statistics
    if total_rewards:
        avg_reward = sum(total_rewards) / len(total_rewards)
        avg_steps = sum(total_steps) / len(total_steps)
        
        print(f"\n" + "="*50)
        print(f"EVALUATION RESULTS")
        print(f"="*50)
        print(f"Episodes completed: {len(total_rewards)}")
        print(f"Average reward: {avg_reward:.2f}")
        print(f"Min reward: {min(total_rewards):.2f}")
        print(f"Max reward: {max(total_rewards):.2f}")
        print(f"Average steps: {avg_steps:.1f}")
        print(f"Reward function: {args.reward_fn}")
        
        # Show reward function explanation
        reward_descriptions = SumoRLWrapper.get_available_reward_functions()
        print(f"Reward description: {reward_descriptions.get(args.reward_fn, 'Unknown')}")
    else:
        print("No episodes completed successfully!")


if __name__ == "__main__":
    main()