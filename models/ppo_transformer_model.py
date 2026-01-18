#!/usr/bin/env python3
"""Custom PPO-Transformer model for RLlib (Torch)."""

from __future__ import annotations

from typing import List

import torch
import torch.nn as nn
from ray.rllib.models.torch.torch_modelv2 import TorchModelV2


class PPOTransformerModel(TorchModelV2, nn.Module):
    def __init__(self, obs_space, action_space, num_outputs, model_config, name, **kwargs):
        TorchModelV2.__init__(self, obs_space, action_space, num_outputs, model_config, name)
        nn.Module.__init__(self)

        if len(obs_space.shape) != 2:
            raise ValueError("Observation space must be (L, D)")

        self.seq_len, self.obs_dim = obs_space.shape

        custom = model_config.get("custom_model_config", {})
        d_model = int(custom.get("d_model", 64))
        nhead = int(custom.get("nhead", 4))
        num_layers = int(custom.get("num_layers", 2))
        ff_dim = int(custom.get("ff_dim", 128))
        dropout = float(custom.get("dropout", 0.1))

        self.input_proj = nn.Linear(self.obs_dim, d_model)
        self.pos_embed = nn.Parameter(torch.zeros(self.seq_len, d_model))

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=ff_dim,
            dropout=dropout,
            batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        self.phase_head = nn.Linear(d_model, 2)
        self.duration_head = nn.Linear(d_model, 3)
        self.value_head = nn.Linear(d_model, 1)

        self._value = None

    def forward(self, input_dict, state, seq_lens):
        x = input_dict["obs"]
        if x.dtype != torch.float32:
            x = x.float()

        x = self.input_proj(x)
        x = x + self.pos_embed.unsqueeze(0)
        x = self.encoder(x)

        h = x[:, -1, :]

        phase_logits = self.phase_head(h)
        duration_logits = self.duration_head(h)
        self._value = self.value_head(h).squeeze(1)

        logits = torch.cat([phase_logits, duration_logits], dim=-1)
        return logits, state

    def value_function(self):
        return self._value
