"""Dependency serialization tests."""

import pytest
from pydantic import BaseModel

from paigeant.deps.deserializer import DependencyDeserializer
from paigeant.deps.serializer import DependencySerializer


class MockDeps(BaseModel):
    api_key: str = "test-key"
    timeout: int = 30


@pytest.mark.asyncio
async def test_pydantic_model_serialization():
    """Test serializing and deserializing Pydantic models."""
    deps = MockDeps(api_key="secret", timeout=60)

    # Serialize
    data, type_name, module = DependencySerializer.serialize(deps)

    assert data == {"api_key": "secret", "timeout": 60}

    # Deserialize
    restored = DependencyDeserializer.deserialize(data, type_name, module)

    assert isinstance(restored, MockDeps)
    assert restored.api_key == "secret"
    assert restored.timeout == 60


@pytest.mark.asyncio
async def test_none_serialization():
    """Test handling None dependencies."""
    data, type_name, module = DependencySerializer.serialize(None)

    restored = DependencyDeserializer.deserialize(data, type_name, module)

    assert restored is None
