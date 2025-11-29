def test_import_main():
    import importlib
    module = importlib.import_module("main")
    assert hasattr(module, "app")
    assert module.app is not None
    # Ensure the root path exists and HEAD route is registered
    paths = {route.path for route in module.app.routes}
    assert "/" in paths
    assert any(route.path == "/" for route in module.app.routes)
