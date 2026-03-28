def test_app_is_importable():
    from app.main import app
    assert app is not None


def test_get_db_yields_session():
    from app.dependencies import get_db
    import inspect
    assert inspect.isgeneratorfunction(get_db)
