#!/usr/bin/env python3
"""
Run one long PPO-Transformer simulation with GUI using config from tune/baseline.
"""

import argparse
from pathlib import Path

import yaml

from envs.ppo_transformer_env import PPOTransformerEnv


def main():
    parser = argparse.ArgumentParser(description="Run one long simulation with GUI")
    parser.add_argument(
        "--config",
        default="configs/ppo_transformer_baseline.yaml",
        help="Config YAML (default: baseline)",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=14400,
        help="Simulation end time in seconds (default: 14400 = 4h)",
    )
    args = parser.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        cfg_path = Path(__file__).resolve().parent.parent / args.config
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)

    env_config = dict(cfg.get("env_config", {}))
    env_config["use_gui"] = True
    env_config["sumo_binary"] = "sumo-gui"
    env_config["sim_end"] = args.steps

    print(f"Starting simulation: {args.steps}s ({args.steps/3600:.1f}h) with GUI")
    print(f"Config: {args.config}")

    env = PPOTransformerEnv(env_config)
    obs, _ = env.reset()
    done = False
    step = 0
    while not done:
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        step += 1
        if step % 100 == 0:
            print(f"  Step {step}, reward={reward:.1f}")

    env.close()
    print(f"Done after {step} steps")


if __name__ == "__main__":
    main()
