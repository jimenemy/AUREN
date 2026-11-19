"""Codespaces launch must preserve Streamlit's browser security boundaries."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CodespacesSecurityRegression(unittest.TestCase):
    def test_streamlit_server_has_cors_and_xsrf_enabled(self):
        config = (ROOT / ".devcontainer" / "devcontainer.json").read_text(encoding="utf-8")
        found = re.search(r'"server"\s*:\s*"([^"]+)"', config)
        self.assertIsNotNone(found, "Missing Codespaces server command")
        command = found.group(1)
        for flag in ("enableCORS", "enableXsrfProtection"):
            with self.subTest(flag=flag):
                self.assertEqual(command.count("--server." + flag), 1)
                self.assertRegex(command, r"--server\." + flag + r" true(?:\s|$)")
                self.assertNotRegex(command, r"--server\." + flag + r" false(?:\s|$)")


if __name__ == "__main__":
    unittest.main()
