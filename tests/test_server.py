"""Tests for the development server's /health endpoint."""

import shutil
import tempfile
import unittest

try:
    from tornado import web
    from tornado.testing import AsyncHTTPTestCase

    from pagesmith.server import HealthAwareServer
    SERVER_DEPS_AVAILABLE = True
except ImportError:
    SERVER_DEPS_AVAILABLE = False


@unittest.skipUnless(
    SERVER_DEPS_AVAILABLE,
    "livereload/tornado not available (pip install 'pagesmith[serve]')",
)
class HealthEndpointTest(AsyncHTTPTestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()
        super().setUp()

    def tearDown(self):
        super().tearDown()
        shutil.rmtree(self.root, ignore_errors=True)

    def get_app(self):
        server = HealthAwareServer()
        server.root = self.root
        server.default_filename = 'index.html'
        return web.Application(server.get_web_handlers(''))

    def test_health_route_precedes_static_catch_all(self):
        server = HealthAwareServer()
        server.root = self.root
        server.default_filename = 'index.html'
        handlers = server.get_web_handlers('')
        self.assertEqual(handlers[0][0], r'/health/?$')

    def test_get_health_returns_ok(self):
        response = self.fetch('/health')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, b'ok')

    def test_get_health_trailing_slash(self):
        response = self.fetch('/health/')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, b'ok')

    def test_head_health_returns_ok(self):
        response = self.fetch('/health', method='HEAD')
        self.assertEqual(response.code, 200)

    def test_unknown_path_still_404s(self):
        response = self.fetch('/no-such-file')
        self.assertEqual(response.code, 404)


if __name__ == '__main__':
    unittest.main()