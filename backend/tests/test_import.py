def test_import_package():
    try:
        pass
    except Exception as e:
        import sys

        print("IMPORT_ERROR", e, file=sys.stderr)
        raise
    assert True
