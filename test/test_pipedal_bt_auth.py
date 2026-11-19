#!/usr/bin/env python3
"""HTTP PIN gate: compare typed PIN, then unlock PiPedal."""
import importlib.machinery
import importlib.util
import os
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "scripts"))


def load_auth():
    path = os.path.join(SCRIPTS, "pipedal-bt-auth")
    loader = importlib.machinery.SourceFileLoader("pipedal_bt_auth", path)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class HttpPinGateTest(unittest.TestCase):
    def setUp(self):
        self.mod = load_auth()
        self.mod.nft_lock = lambda: True
        self.mod.nft_unlock = lambda: None
        self.pin_file = tempfile.NamedTemporaryFile("w", delete=False)
        self.pin_file.write("* 001037\n")
        self.pin_file.close()
        self.unlocked = tempfile.NamedTemporaryFile("w", delete=False)
        self.unlocked.close()
        os.unlink(self.unlocked.name)
        self.mod.PIN_FILE = self.pin_file.name
        self.mod.UNLOCKED = self.unlocked.name
        self.httpd = self.mod.HTTPServer(("127.0.0.1", 0), self.mod.Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.05)

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        os.unlink(self.pin_file.name)
        if os.path.exists(self.unlocked.name):
            os.unlink(self.unlocked.name)

    def _opener(self):
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None

        return urllib.request.build_opener(NoRedirect)

    def _post(self, pin):
        data = f"pin={pin}".encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/", data=data, method="POST"
        )
        return self._opener().open(req, timeout=2)

    def test_wrong_pin_stays_locked(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._post("0000")
        self.assertEqual(ctx.exception.code, 403)
        self.assertFalse(os.path.exists(self.unlocked.name))

    def test_001037_unlocks(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._post("001037")
        self.assertEqual(ctx.exception.code, 302)
        self.assertTrue(os.path.exists(self.unlocked.name))

    def test_1037_unlocks_same_pin(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._post("1037")
        self.assertEqual(ctx.exception.code, 302)
        self.assertTrue(os.path.exists(self.unlocked.name))

    def test_get_shows_form_while_locked(self):
        body = urllib.request.urlopen(f"http://127.0.0.1:{self.port}/", timeout=2).read()
        self.assertIn(b"name=\"pin\"", body)


if __name__ == "__main__":
    unittest.main()
