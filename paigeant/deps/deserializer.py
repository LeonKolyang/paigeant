import importlib
from typing import Any

from pydantic import BaseModel


class DependencyDeserializer:
    """
    Safely reconstruct a dependency from serialized data and metadata.

    Supports:
    - Pydantic models
    - Plain dicts
    - Reference strings for deferred local instantiation
    """

    @staticmethod
    def deserialize(
        deps_data: dict | str | None,
        deps_type: str | None,
        deps_module: str | None,
        fallback_module: str | None = None,
    ) -> Any:
        if deps_data is None:
            return None

        if isinstance(deps_data, str) and deps_type == "str":
            return deps_data

        if not deps_type or not deps_module:
            raise ValueError("Missing dependency type or module metadata")

        try:
            if deps_module == "__main__" and fallback_module:
                module = importlib.import_module(fallback_module)
            else:
                module = importlib.import_module(deps_module)

            deps_class = getattr(module, deps_type)

            if issubclass(deps_class, BaseModel):
                return deps_class.model_validate(deps_data)

            return deps_class(**deps_data)

        except Exception as e:
            raise ValueError(
                f"Failed to reconstruct dependency '{deps_type}' from module '{deps_module}': {e}"
            )
