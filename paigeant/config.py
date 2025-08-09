from __future__ import annotations

import os
from typing import Optional, Literal

import yaml
from pydantic import BaseModel


class RedisConfig(BaseModel):
    """Configuration for Redis transport."""

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None


class TransportConfig(BaseModel):
    """Transport configuration settings."""

    backend: Literal["inmemory", "redis"] = "inmemory"
    redis: RedisConfig = RedisConfig()


class PaigeantConfig(BaseModel):
    """Top-level configuration model."""

    transport: TransportConfig = TransportConfig()


def load_config(path: Optional[str] = None) -> PaigeantConfig:
    """Load configuration from YAML file.

    Args:
        path: Optional path to config file. Falls back to PAIGENT_CONFIG env
            variable or 'config.yaml' in the current directory.
    """

    config_path = path or os.getenv("PAIGENT_CONFIG", "config.yaml")
    if os.path.exists(config_path):
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        return PaigeantConfig(**data)
    return PaigeantConfig()
