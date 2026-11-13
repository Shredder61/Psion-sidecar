import contextlib
import io
import sys
import unittest
from unittest.mock import patch, MagicMock

import sidecar_web


class TestServerPort(unittest.TestCase):

    def run_main(self, arguments):
        fake_server = MagicMock()

        with (
            patch.object(sys, "argv", ["sidecar_web.py"] + arguments),
            patch.object(
                sidecar_web,
                "ThreadingHTTPServer",
                return_value=fake_server
            ) as server_class,
            contextlib.redirect_stdout(io.StringIO())
        ):
            sidecar_web.main()

        return server_class, fake_server

    def test_default_port_is_8081(self):
        server_class, fake_server = self.run_main([])

        self.assertEqual(
            server_class.call_args.args[0],
            ("0.0.0.0", 8081)
        )
        fake_server.serve_forever.assert_called_once()
        fake_server.server_close.assert_called_once()

    def test_custom_port_8082(self):
        server_class, _ = self.run_main(["--port", "8082"])

        self.assertEqual(
            server_class.call_args.args[0],
            ("0.0.0.0", 8082)
        )

    def test_custom_port_8083(self):
        server_class, _ = self.run_main(["--port", "8083"])

        self.assertEqual(
            server_class.call_args.args[0],
            ("0.0.0.0", 8083)
        )

    def test_port_zero_rejected(self):
        with (
            patch.object(sys, "argv", ["sidecar_web.py", "--port", "0"]),
            patch.object(sidecar_web, "ThreadingHTTPServer") as server_class,
            contextlib.redirect_stderr(io.StringIO())
        ):
            with self.assertRaises(SystemExit) as error:
                sidecar_web.main()

        self.assertEqual(error.exception.code, 2)
        server_class.assert_not_called()

    def test_port_above_range_rejected(self):
        with (
            patch.object(
                sys, "argv",
                ["sidecar_web.py", "--port", "65536"]
            ),
            patch.object(sidecar_web, "ThreadingHTTPServer") as server_class,
            contextlib.redirect_stderr(io.StringIO())
        ):
            with self.assertRaises(SystemExit) as error:
                sidecar_web.main()

        self.assertEqual(error.exception.code, 2)
        server_class.assert_not_called()

    def test_help_option(self):
        with (
            patch.object(sys, "argv", ["sidecar_web.py", "--help"]),
            contextlib.redirect_stdout(io.StringIO()) as output
        ):
            with self.assertRaises(SystemExit) as error:
                sidecar_web.main()

        self.assertEqual(error.exception.code, 0)
        self.assertIn("--port PORT", output.getvalue())
        self.assertIn("default: 8081", output.getvalue())


if __name__ == "__main__":
    unittest.main()
