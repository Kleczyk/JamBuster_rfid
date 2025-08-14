#!/usr/bin/env python3
"""Training script for RL traffic control agents."""

import argparse
import logging
from pathlib import Path

import hydra
from omegaconf import DictConfig


@hydra.main(version_base=None, config_path="../experiments/configs", config_name="base_config")
def main(cfg: DictConfig) -> None:
    """Main training function."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting experiment: {cfg.experiment.name}")
    # TODO: Implement training logic


if __name__ == "__main__":
    main()