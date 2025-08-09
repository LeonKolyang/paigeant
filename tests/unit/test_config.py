"""Tests for configuration loading."""

from paigeant.config import load_config
from paigeant.transports import get_transport
from paigeant.transports.redis import RedisTransport


def test_load_config_from_env(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
transport:
  backend: redis
  redis:
    host: testhost
    port: 1234
"""
    )
    monkeypatch.setenv("PAIGENT_CONFIG", str(config_path))

    config = load_config()
    assert config.transport.backend == "redis"
    assert config.transport.redis.host == "testhost"
    assert config.transport.redis.port == 1234


def test_get_transport_uses_config(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
transport:
  backend: redis
  redis:
    host: confighost
    port: 6380
"""
    )
    monkeypatch.setenv("PAIGENT_CONFIG", str(config_path))

    transport = get_transport()
    assert isinstance(transport, RedisTransport)
    assert transport.host == "confighost"
    assert transport.port == 6380
