#!/usr/bin/env python3
"""
Demo script for PPO-Transformer: evaluation on training, baseline, and baseline_noise scenarios.

This script:
1. Loads a trained model from checkpoint
2. Runs evaluation on training scenario (simulation.sumocfg)
3. Runs evaluation on baseline scenario (simulation_test.sumocfg, no noise)
4. Runs evaluation on baseline_noise scenario (simulation_test.sumocfg, with RFID noise)
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Optional

import ray
import yaml
from ray.rllib.algorithms.ppo import PPO
from ray.rllib.models import ModelCatalog
from ray.tune.registry import register_env

from envs.ppo_transformer_env import PPOTransformerEnv
from models.ppo_transformer_model import PPOTransformerModel
from train_ppo_transformer import load_config, build_config, _resolve_sumo_cfg_path, _apply_ray_env


def run_evaluation(algo: PPO, env_config: dict, num_episodes: int = 5, label: str = "Evaluation"):
    """Run evaluation episodes."""
    print(f"\n{'='*80}")
    print(f"DEMO: {label}")
    print("="*80)
    
    env = PPOTransformerEnv(env_config)
    obs, info = env.reset()
    
    episode_rewards = []
    episode_lengths = []
    episode_metrics = []
    
    for episode in range(num_episodes):
        episode_reward = 0.0
        episode_length = 0
        episode_info = {}
        
        done = False
        truncated = False
        
        while not (done or truncated):
            action = algo.compute_single_action(obs, explore=False)
            obs, reward, terminated, truncated, info = env.step(action)
            episode_reward += reward
            episode_length += 1
            done = terminated
            
            # Collect metrics from info
            if info:
                for key, value in info.items():
                    if key not in episode_info:
                        episode_info[key] = []
                    episode_info[key].append(value)
        
        episode_rewards.append(episode_reward)
        episode_lengths.append(episode_length)
        
        # Calculate average metrics for this episode
        avg_metrics = {}
        for key, values in episode_info.items():
            if values:
                avg_metrics[key] = sum(values) / len(values)
        episode_metrics.append(avg_metrics)
        
        print(f"\nEpisode {episode + 1}/{num_episodes}:")
        print(f"  Reward: {episode_reward:.2f}")
        print(f"  Length: {episode_length}")
        if avg_metrics:
            print(f"  Metrics:")
            for key, value in avg_metrics.items():
                print(f"    {key}: {value:.2f}")
        
        obs, info = env.reset()
    
    env.close()
    
    # Summary
    avg_reward = sum(episode_rewards) / len(episode_rewards)
    avg_length = sum(episode_lengths) / len(episode_lengths)
    
    print(f"\n{label} Summary:")
    print(f"  Average Reward: {avg_reward:.2f}")
    print(f"  Average Length: {avg_length:.2f}")
    
    if episode_metrics:
        print(f"  Average Metrics:")
        for key in episode_metrics[0].keys():
            avg_value = sum(m.get(key, 0) for m in episode_metrics) / len(episode_metrics)
            print(f"    {key}: {avg_value:.2f}")
    
    return {
        "rewards": episode_rewards,
        "lengths": episode_lengths,
        "metrics": episode_metrics,
        "avg_reward": avg_reward,
        "avg_length": avg_length,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Demo: Evaluation on training, baseline, and baseline_noise scenarios")
    parser.add_argument("--config", default="configs/ppo_transformer_baseline.yaml", help="Config YAML")
    parser.add_argument("--checkpoint", type=str, required=True, help="Path to checkpoint (required)")
    parser.add_argument("--eval-episodes", type=int, default=5, help="Number of evaluation episodes")
    parser.add_argument("--gui", action="store_true", help="Show SUMO GUI during evaluation")
    args = parser.parse_args()
    
    # Load config
    cfg = load_config(Path(args.config))
    _apply_ray_env(cfg)
    
    # Initialize Ray
    resources_cfg = cfg.get("resources", {})
    ray.init(
        num_cpus=resources_cfg.get("num_cpus", 4),
        num_gpus=resources_cfg.get("num_gpus", 0),
    )
    
    # Register environment and model
    env_name = cfg.get("env_name", "ppo_transformer_env")
    register_env(env_name, lambda env_cfg: PPOTransformerEnv(env_cfg))
    ModelCatalog.register_custom_model("ppo_transformer_model", PPOTransformerModel)
    
    # Check checkpoint exists
    checkpoint_path = Path(args.checkpoint)
    if not checkpoint_path.exists():
        print(f"\nERROR: Checkpoint not found: {checkpoint_path}")
        print("Please provide a valid checkpoint path.")
        return 1
    
    print(f"\n{'='*80}")
    print("DEMO: Loading Trained Model")
    print("="*80)
    print(f"Checkpoint: {checkpoint_path}")
    
    # Build config for loading
    try:
        ppo_cfg = build_config(cfg)
        algo = PPO.from_checkpoint(str(checkpoint_path), config=ppo_cfg.to_dict())
        print("Model loaded successfully!")
    except Exception as e:
        print(f"\nERROR: Failed to load checkpoint: {e}")
        print("Please check that the checkpoint path is correct and compatible with the config.")
        return 1
    
    # Base env config from training config
    base_env_config = dict(cfg.get("env_config", {}))
    base_env_config = _resolve_sumo_cfg_path(base_env_config)
    if args.gui:
        base_env_config["use_gui"] = True
    
    # 1. Training scenario (simulation.sumocfg)
    training_env_config = dict(base_env_config)
    training_env_config["sumo_cfg"] = _resolve_sumo_cfg_path({"sumo_cfg": "nets/ppo_transformer_intersection/simulation.sumocfg"}).get("sumo_cfg")
    training_env_config["rfid_noise_rate"] = 0.0
    
    training_results = run_evaluation(
        algo,
        training_env_config,
        num_episodes=args.eval_episodes,
        label="Training Scenario (simulation.sumocfg)"
    )
    
    # 2. Baseline scenario (simulation_test.sumocfg, no noise)
    baseline_env_config = dict(base_env_config)
    baseline_env_config["sumo_cfg"] = _resolve_sumo_cfg_path({"sumo_cfg": "nets/ppo_transformer_intersection/simulation_test.sumocfg"}).get("sumo_cfg")
    baseline_env_config["rfid_noise_rate"] = 0.0
    
    baseline_results = run_evaluation(
        algo,
        baseline_env_config,
        num_episodes=args.eval_episodes,
        label="Baseline Scenario (simulation_test.sumocfg, no noise)"
    )
    
    # 3. Baseline noise scenario (simulation_test.sumocfg, with RFID noise)
    baseline_noise_env_config = dict(base_env_config)
    baseline_noise_env_config["sumo_cfg"] = _resolve_sumo_cfg_path({"sumo_cfg": "nets/ppo_transformer_intersection/simulation_test.sumocfg"}).get("sumo_cfg")
    baseline_noise_env_config["rfid_noise_rate"] = 0.2
    
    baseline_noise_results = run_evaluation(
        algo,
        baseline_noise_env_config,
        num_episodes=args.eval_episodes,
        label="Baseline Noise Scenario (simulation_test.sumocfg, RFID noise=0.2)"
    )
    
    # Final summary
    print("\n" + "="*80)
    print("DEMO SUMMARY")
    print("="*80)
    print(f"Checkpoint used: {checkpoint_path}")
    print(f"\nResults Comparison:")
    print(f"  {'Scenario':<40} {'Avg Reward':<15} {'Avg Length':<15}")
    print(f"  {'-'*40} {'-'*15} {'-'*15}")
    print(f"  {'Training (simulation.sumocfg)':<40} {training_results['avg_reward']:>15.2f} {training_results['avg_length']:>15.2f}")
    print(f"  {'Baseline (test, no noise)':<40} {baseline_results['avg_reward']:>15.2f} {baseline_results['avg_length']:>15.2f}")
    print(f"  {'Baseline Noise (test, noise=0.2)':<40} {baseline_noise_results['avg_reward']:>15.2f} {baseline_noise_results['avg_length']:>15.2f}")
    print("="*80)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
