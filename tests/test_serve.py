"""Tests of the local preview server.

The one guarantee worth testing is the reason it exists: a request for a route —
`/records/IGNF_BD-TOPO` — is answered with the application rather than with a 404,
the way GitHub Pages answers it with the `404.html` the build writes.

The server binds loopback on a port the kernel picks, so the suite stays offline in
the sense that matters: nothing leaves the machine.
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import threading
from functools import partial
from http.server import HTTPServer
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from gpf_catalogue.serve import SinglePageHandler, serve


@pytest.fixture
def site(tmp_path):
    """A built site, reduced to what the server has to tell apart."""
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html>entry", encoding="utf-8")
    (tmp_path / "404.html").write_text("<!doctype html>entry", encoding="utf-8")
    (tmp_path / "catalogue.json").write_text('{"count": 0}', encoding="utf-8")
    (tmp_path / "assets" / "index-aaa.js").write_text("/* bundle */", encoding="utf-8")
    return tmp_path


@pytest.fixture
def base_url(site):
    """Serve `site` on a loopback port, and stop when the test ends."""
    handler = partial(SinglePageHandler, directory=str(site))
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def get(url: str) -> str:
    with urlopen(url, timeout=5) as response:
        return response.read().decode("utf-8")


def test_a_record_route_is_answered_with_the_application(base_url):
    """This is the whole point: a link to a record works when pasted."""
    assert "entry" in get(f"{base_url}/records/IGNF_BD-TOPO")


def test_an_identifier_that_looks_like_a_file_is_still_a_route(base_url):
    """Nine identifiers end in `.xml`, and they are records, not documents."""
    assert "entry" in get(f"{base_url}/records/BDML_DELMAR.xml")


def test_the_other_routes_too(base_url):
    for route in ("/overview", "/records", "/quality"):
        assert "entry" in get(f"{base_url}{route}")


def test_a_real_file_is_served_as_itself(base_url):
    assert get(f"{base_url}/catalogue.json") == '{"count": 0}'
    assert get(f"{base_url}/assets/index-aaa.js") == "/* bundle */"


def test_a_missing_asset_stays_a_404(base_url):
    """A stale bundle must fail loudly, not quietly return the entry document."""
    with pytest.raises(HTTPError) as failure:
        get(f"{base_url}/assets/index-gone.js")
    assert failure.value.code == 404


def test_serving_a_directory_without_a_site_is_reported(tmp_path):
    with pytest.raises(FileNotFoundError, match="build_site"):
        serve(tmp_path)
