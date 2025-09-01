"""Tests for registry data models."""

from datetime import datetime

from paigeant.registry import (
    AgentDescriptor,
    Group,
    ParamDescriptor,
    RegistryRoot,
    SemanticVersion,
)


def test_semantic_version_parsing_and_string() -> None:
    sv = SemanticVersion.parse("1.2.3")
    assert (sv.major, sv.minor, sv.patch) == (1, 2, 3)
    assert str(sv) == "1.2.3"


def test_param_descriptor_defaults() -> None:
    param = ParamDescriptor(name="foo", type_ref="int")
    assert param.required is True
    assert param.default_json is None


def test_agent_descriptor_defaults() -> None:
    agent = AgentDescriptor(
        name="echo",
        version=SemanticVersion(major=1, minor=0, patch=0),
        transport="redis",
        address="queue.echo",
    )
    assert agent.permissions == []
    assert agent.inputs == []
    assert agent.outputs == []
    assert agent.supported_prompts == []


def test_registry_root_structure() -> None:
    agent = AgentDescriptor(
        name="echo",
        version=SemanticVersion.parse("1.0.0"),
        transport="redis",
        address="queue.echo",
    )
    group = Group(name="default", agents=[agent])
    snapshot = RegistryRoot(groups=[group])

    assert snapshot.schema_version == "1"
    assert snapshot.groups[0].agents[0].name == "echo"
    assert isinstance(snapshot.generated_at, datetime)
