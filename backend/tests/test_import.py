def test_import_package():
    try:
        import ai_routing_layer
    except Exception as e:
        import sys
        print('IMPORT_ERROR', e, file=sys.stderr)
        raise
    assert True
