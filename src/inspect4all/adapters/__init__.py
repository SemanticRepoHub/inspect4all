from inspect4all.adapters.registry import AdapterRegistry

__all__ = ["AdapterRegistry", "build_default_registry"]


def build_default_registry() -> AdapterRegistry:
    """Registry with all built-in language adapters.

    Adding support for a new language means registering its adapter here
    (see "Adding a new language" in the README).
    """
    from inspect4all.adapters.java.adapter import JavaAdapter
    from inspect4all.adapters.python.adapter import PythonAdapter

    return AdapterRegistry(PythonAdapter(), JavaAdapter())
