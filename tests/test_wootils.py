import wootils


def test_fetch_no_cache_doesnt_screw_up():
    assert wootils.fetch_no_cache('http://www.google.com').status_code == 200

# TODO: Make up this test once you have async code.
# def test_no_cache_async_fetch():
#     pass

