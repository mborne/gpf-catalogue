"""A static file server that knows the site has routes.

`python -m http.server` serves the site correctly right up to the moment a record
is linked to: `/records/IGNF_BD-TOPO` is a route of the application, not a file, so
it answers 404 and the link that the rewrite exists for does not survive being
pasted anywhere.

GitHub Pages solves this with `404.html`, which the build writes as a copy of the
entry document; a local server has no such convention, so this one applies the same
rule directly — a request for something that is not a file, and does not look like
one, is answered with the entry document, and the router reads the path from there.

Nothing else is added: no cache header, no compression, no directory listing worth
mentioning. This serves a built `site/` for a browser on the same machine.
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import logging
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

logger = logging.getLogger(__name__)

#: Entry document, served for any path that is a route rather than a file.
INDEX_NAME = "index.html"

#: First segment of every route the application declares. Listing them, rather
#: than answering anything missing with the entry document, keeps a stale asset a
#: 404: `/assets/index-gone.js` is a broken build, and saying so beats quietly
#: serving it a HTML document the browser cannot execute.
ROUTES = frozenset({"about", "overview", "records", "quality"})


class SinglePageHandler(SimpleHTTPRequestHandler):
    """Serve files as they are, and the application's routes as the entry document."""

    def send_head(self):
        """Resolve the request, rerouting a route to the entry document."""
        target = Path(self.translate_path(self.path))
        if not target.exists() and self._is_route():
            self.path = f"/{INDEX_NAME}"
        return super().send_head()

    def _is_route(self) -> bool:
        """Whether the requested path is one of the application's routes.

        The suffix says nothing: nine identifiers of the catalogue end in `.xml`,
        so `/records/BDML_DELMAR.xml` is a record and not a document.
        """
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        head = path.lstrip("/").split("/", 1)[0]
        return head in ROUTES


def serve(site_dir: Path, port: int = 8000, host: str = "127.0.0.1") -> None:
    """Serve a built site until interrupted.

    Args:
        site_dir: Directory written by `build_site`.
        port: TCP port to listen on.
        host: Interface to bind. Loopback by default: this is a preview, not a
            deployment.

    Raises:
        FileNotFoundError: If the directory holds no built site.
    """
    if not (site_dir / INDEX_NAME).is_file():
        raise FileNotFoundError(
            f"{site_dir / INDEX_NAME} not found, run 'uv run scripts/build_site.py' first"
        )

    handler = partial(SinglePageHandler, directory=str(site_dir))
    server = HTTPServer((host, port), handler)
    logger.info("serving %s on http://%s:%d/", site_dir, host, port)
    print(f"serving {site_dir} on http://{host}:{port}/ — Ctrl-C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()
