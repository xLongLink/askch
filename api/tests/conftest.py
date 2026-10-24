import runpy
import httpx2
import pytest
import functools
from src import settings
from pathlib import Path


@pytest.fixture
def load_app(monkeypatch, tmp_path):
    """Load the application with isolated configuration and deployment files."""
    # Keep settings and provider transport isolated for each existing test.
    client_type = httpx2.AsyncClient

    # Run the entry point in an isolated deployment directory.
    entrypoint = tmp_path / "main.py"
    entrypoint.write_text((Path(__file__).parents[1] / "main.py").read_text())

    def load(configuration, transport=None):
        # Load the real entry point with explicit test configuration.
        with monkeypatch.context() as configuration_patch:
            configuration_patch.setattr(settings, "settings", configuration)
            namespace = runpy.run_path(str(entrypoint))

        # Intercept only the provider client when a test supplies a transport.
        if transport is not None:
            monkeypatch.setattr(httpx2, "AsyncClient", functools.partial(client_type, transport=transport))
        return namespace["app"]

    return load
