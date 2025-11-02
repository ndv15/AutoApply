"""Serve generated Markdown previews as simple HTML pages.

Usage: python scripts/serve_preview.py [port]
Visit http://localhost:<port>/<draft_id>.md
"""
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import unquote
from pathlib import Path
import sys
import markdown


class PreviewHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # Strip leading slash and decode
        path = unquote(self.path.lstrip("/"))
        # Ensure path is within preview directory
        file_path = Path("preview") / path
        if file_path.exists() and file_path.suffix == ".md":
            md = file_path.read_text(encoding="utf-8")
            html = markdown.markdown(md)
            content = f"<html><head><meta charset='utf-8'></head><body>{html}</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def main(argv: list[str]) -> None:
    port = int(argv[1]) if len(argv) > 1 else 8000
    server = HTTPServer(("", port), PreviewHandler)
    print(f"Serving preview/ on http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main(sys.argv)
