import logging
import unittest

from app.core.logger import HealthCheckAccessFilter, uvicorn_log_config


def access_record(path: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1:1000", "GET", path, "1.1", 200),
        exc_info=None,
    )


class LoggingTests(unittest.TestCase):
    def test_health_probe_paths_are_filtered(self) -> None:
        access_filter = HealthCheckAccessFilter()
        for path in ("/healthz", "/readyz", "/ping", "/healthz?source=render"):
            with self.subTest(path=path):
                self.assertFalse(access_filter.filter(access_record(path)))

    def test_normal_access_logs_remain_visible(self) -> None:
        self.assertTrue(HealthCheckAccessFilter().filter(access_record("/documents/terms")))

    def test_uvicorn_access_handler_uses_filter(self) -> None:
        config = uvicorn_log_config()
        self.assertEqual(config["handlers"]["access"]["filters"], ["skip_health_checks"])


if __name__ == "__main__":
    unittest.main()
