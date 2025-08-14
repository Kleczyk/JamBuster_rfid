#!/usr/bin/env python3
"""Train A3C agent using sumo-rl library with Ray RLlib."""

import argparse
from pathlib import Path

import ray
from ray import tune
from ray.rllib.algorithms.a3c import A3CConfig
from ray.tune.registry import register_env
import sumo_rl


def env_creator(env_config):
    """Create sumo-rl environment."""
    return sumo_rl.env(
        net_file=env_config.get("net_file", "sumo/single_intersection.net.xml"),
        route_file=env_config.get("route_file", "sumo/single_intersection.rou.xml"),
        use_gui=env_config.get("use_gui", False),
        num_seconds=env_config.get("num_seconds", 3600),
        delta_time=env_config.get("delta_time", 5),
        yellow_time=env_config.get("yellow_time", 4),
        sumo_seed=env_config.get("seed", 42),
    )


def main():
    """Main A3C training function."""
    parser = argparse.ArgumentParser(description="Train A3C with sumo-rl")
    parser.add_argument("--gui", action="store_true", help="Use SUMO GUI")
    parser.add_argument("--num-workers", type=int, default=4, help="Number of workers")
    parser.add_argument("--episodes", type=int, default=1000, help="Training episodes")
    parser.add_argument("--checkpoint-freq", type=int, default=100, help="Checkpoint frequency")
    parser.add_argument("--net-file", default="sumo/single_intersection.net.xml", help="SUMO network file")
    parser.add_argument("--route-file", default="sumo/single_intersection.rou.xml", help="SUMO route file")
    
    args = parser.parse_args()
    
    # Initialize Ray
    ray.init(ignore_reinit_error=True)
    
    # Register environment
    register_env("sumo_rl_env", env_creator)
    
    # Configure A3C
    config = (
        A3CConfig()
        .environment(
            env="sumo_rl_env",
            env_config={
                "net_file": args.net_file,
                "route_file": args.route_file,
                "use_gui": args.gui,
                "num_seconds": 3600,
                "delta_time": 5,
                "yellow_time": 4,
                "seed": 42,
            }
        )
        .env_runners(
            num_env_runners=args.num_workers,
            rollout_fragment_length=20,
        )
        .training(
            lr=0.0001,
            gamma=0.99,
            entropy_coeff=0.01,
            vf_loss_coeff=0.5,
            grad_clip=40.0,
        )
        .debugging(log_level="INFO")
    )
    
    # Run training
    tuner = tune.Tuner(
        "A3C",
        param_space=config.to_dict(),
        run_config=tune.RunConfig(
            stop={"episodes_total": args.episodes},
            checkpoint_config=tune.CheckpointConfig(
                checkpoint_frequency=args.checkpoint_freq,
            ),
            storage_path=str(Path("./ray_results").absolute()),
            name="a3c_sumo_rl",
        ),
    )
    
    results = tuner.fit()
    print("A3C Training completed!")
    print(f"Best result: {results.get_best_result()}")


if __name__ == "__main__":
    main()