# file: paigeant/deps/serializer.py

from typing import Any, Tuple


class DependencySerializer:
    """
    Serialize dependency for transmission over the message bus.

    Returns:
        Tuple of (serialized_data, type_name, module_path)
    """

    @staticmethod
    def serialize(deps: Any) -> Tuple[dict | str | None, str | None, str | None]:
        if deps is None:
            return None, None, None

        deps_type = type(deps).__name__
        deps_module = type(deps).__module__

        # If it's a string reference (e.g., token, ID)
        if isinstance(deps, str):
            return deps, "str", "builtins"

        # If it's a Pydantic model
        if hasattr(deps, "model_dump") and callable(deps.model_dump):
            try:
                return deps.model_dump(), deps_type, deps_module
            except Exception as e:
                raise ValueError(f"Failed to serialize Pydantic model {deps_type}: {e}")

        # Try simple serialization via vars()
        try:
            return vars(deps), deps_type, deps_module
        except Exception as e:
            raise ValueError(
                f"Cannot serialize dependency of type '{deps_type}' from module '{deps_module}': {e}"
            )
