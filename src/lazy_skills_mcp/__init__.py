"""An MCP server that serves Agent Skills on demand: discovery, catalog, tools, and CLI."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("lazy-skills-mcp")
except PackageNotFoundError:  # pragma: no cover - only when run from an uninstalled source tree
    __version__ = "0+unknown"
