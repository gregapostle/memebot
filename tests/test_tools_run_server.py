import runpy
import sys
import types

def test_run_server(monkeypatch):
    """Test that run_server calls uvicorn.run with correct args."""
    called = {}

    def fake_run(app, host, port):
        called["app"] = app
        called["host"] = host
        called["port"] = port

    # Monkeypatch uvicorn globally before the module is imported
    fake_uvicorn = types.SimpleNamespace(run=fake_run)
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)

    runpy.run_module("memebot.tools.run_server", run_name="__main__")

    assert called["app"] == "memebot.server:app"
    assert called["host"] == "0.0.0.0"
    assert called["port"] == 8000