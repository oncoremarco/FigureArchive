import importlib
import pkgutil

from figure_archive.plugins import types as types_pkg

# Registry: plugin id -> instantiated plugin
TYPE_PLUGINS: dict[str, object] = {}
SOURCE_PLUGINS: dict[str, object] = {}


def _load_from_package(package, registry: dict) -> None:
    for mod_info in pkgutil.iter_modules(package.__path__):
        if mod_info.name in ("base", "__init__"):
            continue
        module = importlib.import_module(f"{package.__name__}.{mod_info.name}")
        plugin_cls = getattr(module, "PLUGIN", None)
        if plugin_cls is None:
            continue
        instance = plugin_cls()
        registry[instance.id] = instance


def load_plugins() -> None:
    TYPE_PLUGINS.clear()
    SOURCE_PLUGINS.clear()
    _load_from_package(types_pkg, TYPE_PLUGINS)

    # Source plugins (Phase 6+). Load the package only if it has real plugins.
    try:
        from figure_archive.plugins import sources as sources_pkg
        _load_from_package(sources_pkg, SOURCE_PLUGINS)
    except Exception as exc:  # noqa: BLE001
        print(f"[plugins] source loading skipped: {exc}")

    print(f"[plugins] type plugins: {sorted(TYPE_PLUGINS)}")
    print(f"[plugins] source plugins: {sorted(SOURCE_PLUGINS)}")


def get_type_plugin(type_id: str | None):
    """Return the type plugin for an id, falling back to generic."""
    if type_id and type_id in TYPE_PLUGINS:
        return TYPE_PLUGINS[type_id]
    return TYPE_PLUGINS.get("generic")


def list_type_plugins() -> list:
    return [TYPE_PLUGINS[k] for k in sorted(TYPE_PLUGINS, key=lambda i: TYPE_PLUGINS[i].name)]
