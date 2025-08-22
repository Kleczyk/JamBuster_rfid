"""
Training script for a single intersection traffic signal control using SUMO-RL and RLlib.

This script registers a custom environment based on a single SUMO intersection and trains
a PPO policy on it. Environments are executed in parallel via Ray RLlib env runners to
speed up experience collection. See README.md for usage instructions.
"""

import os
import argparse
import importlib.resources

import ray
from ray import tune
from ray.rllib.algorithms.ppo import PPOConfig
from ray.tune.registry import register_env

from sumo_rl import SumoEnvironment


def parse_args():
    p = argparse.ArgumentParser(description="Train PPO on a single SUMO intersection (SUMO-RL + RLlib)")

    # SUMO/ENV
    p.add_argument("--gui", action="store_true", help="Włącz SUMO-GUI (domyślnie wyłączone).")
    p.add_argument("--num-seconds", type=int, default=100_000, help="Długość symulacji w sekundach.")
    p.add_argument("--delta-time", type=int, default=5, help="Liczba sekund między akcjami.")
    p.add_argument("--yellow-time", type=int, default=2, help="Długość fazy żółtej.")
    p.add_argument("--min-green", type=int, default=5, help="Minimalny czas zielonego.")
    p.add_argument("--out-csv", type=str, default=None, help="Ścieżka do CSV z metrykami (lub pusta, by wyłączyć).")
    p.add_argument("--sumo-seed", type=str, default="random", help="Seed dla SUMO (np. 42 lub 'random').")
    p.add_argument("--sumo-warnings", action="store_true", help="Pokaż ostrzeżenia SUMO.")
    p.add_argument("--additional-sumo-cmd", type=str, default=None,
                   help="Dodatkowe argumenty linii poleceń do SUMO (np. '--time-to-teleport -1').")



    p.add_argument("--net-file", type=str, default=None, help="Ścieżka do .net.xml (nadpisuje wbudowane).")
    p.add_argument("--route-file", type=str, default=None, help="Ścieżka do .rou.xml (nadpisuje wbudowane).")


    # RLlib / równoległość
    p.add_argument("--num-env-runners", type=int, default=4,
                   help="Liczba równoległych env runners (dawniej num_rollout_workers).")
    p.add_argument("--num-envs-per-runner", type=int, default=1,
                   help="Liczba envów na jeden runner (vectorized envs).")
    p.add_argument("--rollout-fragment-length", type=int, default=128,
                   help="Długość fragmentu rolloutu przed wysyłką do learnera.")
    p.add_argument("--batch-mode", type=str, default="truncate_episodes",
                   choices=["truncate_episodes", "complete_episodes"],
                   help="Tryb batchowania w RLlib.")

    # Hiperparametry PPO
    p.add_argument("--train-batch-size", type=int, default=512)
    p.add_argument("--sgd-minibatch-size", type=int, default=64)
    p.add_argument("--num-sgd-iter", type=int, default=10)
    p.add_argument("--lr", type=float, default=2e-5)
    p.add_argument("--gamma", type=float, default=0.95)
    p.add_argument("--lambda_", type=float, default=0.9)
    p.add_argument("--clip-param", type=float, default=0.4)
    p.add_argument("--entropy-coeff", type=float, default=0.1)
    p.add_argument("--vf-loss-coeff", type=float, default=0.25)
    p.add_argument("--grad-clip", type=float, default=None, nargs="?",
                   help="Maks. norma gradientu (domyślnie None).")

    # Eksperyment/Tune
    p.add_argument("--stop-timesteps", type=int, default=100_000, help="Koniec po tylu timesteps.")
    p.add_argument("--checkpoint-freq", type=int, default=10, help="Częstotliwość checkpointów (iteracje).")
    p.add_argument("--storage-path", type=str,
                   default=os.path.expanduser("~/ray_results/single_intersection"),
                   help="Katalog na wyniki/artefakty.")
    p.add_argument("--num-gpus", type=int, default=int(os.environ.get("RLLIB_NUM_GPUS", "0")),
                   help="Liczba GPU dla learnera.")
    return p.parse_args()


def create_single_intersection_env(env_config):
    import importlib.resources
    # domyślne (pakietowe)
    default_net = importlib.resources.files("sumo_rl").joinpath(
        "nets/2way-single-intersection/single-intersection.net.xml"
    )
    default_rou = importlib.resources.files("sumo_rl").joinpath(
        "nets/2way-single-intersection/single-intersection-vhvh.rou.xml"
    )

    net_file = env_config.get("net_file") or str(default_net)
    route_file = env_config.get("route_file") or str(default_rou)

    return SumoEnvironment(
        net_file=net_file,
        route_file=route_file,
        out_csv_name=env_config.get("out_csv_name", None),
        use_gui=env_config.get("use_gui", False),
        single_agent=True,
        num_seconds=env_config.get("num_seconds", 100000),
        delta_time=env_config.get("delta_time", 5),
        yellow_time=env_config.get("yellow_time", 2),
        min_green=env_config.get("min_green", 5),
        sumo_seed=env_config.get("sumo_seed", "random"),
        sumo_warnings=env_config.get("sumo_warnings", False),
        additional_sumo_cmd=env_config.get("additional_sumo_cmd", None),
    )



if __name__ == "__main__":
    args = parse_args()

    # Inicjalizacja Ray (lokalnie) – na klastrze: ray.init(address="auto")
    ray.init()

    env_name = "single_intersection_env"
    register_env(env_name, lambda config: create_single_intersection_env(config))

    # Konfiguracja PPO (nowy API stack RLlib)
    config = (
        PPOConfig()
        .environment(
            env=env_name,
            disable_env_checking=True,
            env_config={
                "net_file": args.net_file,
                "route_file": args.route_file,
                "use_gui": args.gui,
                "num_seconds": args.num_seconds,
                "delta_time": args.delta_time,
                "yellow_time": args.yellow_time,
                "min_green": args.min_green,
                "out_csv_name": args.out_csv,
                "sumo_seed": args.sumo_seed,
                "sumo_warnings": args.sumo_warnings,
                "additional_sumo_cmd": args.additional_sumo_cmd,
            },
        )
        .env_runners(
            num_env_runners=args.num_env_runners,
            num_envs_per_env_runner=args.num_envs_per_runner,
            rollout_fragment_length=args.rollout_fragment_length,
            batch_mode=args.batch_mode,  # "truncate_episodes" lub "complete_episodes"
        )
        .training(
            train_batch_size=args.train_batch_size,
            num_sgd_iter=args.num_sgd_iter,
            lr=args.lr,
            gamma=args.gamma,
            lambda_=args.lambda_,
            use_gae=True,
            clip_param=args.clip_param,
            grad_clip=args.grad_clip,
            entropy_coeff=args.entropy_coeff,
            vf_loss_coeff=args.vf_loss_coeff,
        )
        .framework(framework="torch")
        .debugging(log_level="ERROR")
        .resources(num_gpus=args.num_gpus)
    )

    # Uruchomienie eksperymentu przez Ray Tune
    tune.run(
        "PPO",
        name="PPO_single_intersection",
        stop={"timesteps_total": args.stop_timesteps},
        checkpoint_freq=args.checkpoint_freq,
        storage_path=args.storage_path,
        config=config.to_dict(),
    )
