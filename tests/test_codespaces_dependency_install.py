"""Keep Codespaces dependency installation pinned and fail closed."""
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def update_command():
    config = (ROOT / ".devcontainer/devcontainer.json").read_text(encoding="utf-8")
    match = re.search(r'(?m)^  "updateContentCommand": "([^"]+)",$', config)
    if not match:
        raise AssertionError("Missing Codespaces update command")
    return match.group(1)


class CodespacesDependencyInstall(unittest.TestCase):
    def test_use_only_pinned_requirements_without_os_upgrade(self):
        command = update_command()
        self.assertIn("set -eu;", command)
        self.assertNotRegex(command, r"\b(?:apt|apt-get)\s+(?:dist-)?upgrade\b")
        self.assertEqual(command.count("pip install"), 1)
        self.assertIn("python3 -m pip install --user -r requirements.txt", command)
        self.assertNotIn("pip3 install --user streamlit", command)
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertRegex(requirements, r"(?m)^streamlit==[0-9]+\.[0-9]+\.[0-9]+$")

    @unittest.skipUnless(shutil.which("bash"), "bash not available")
    def test_without_optional_apt_packages_uses_one_pinned_pip_install(self):
        with tempfile.TemporaryDirectory(prefix="codespaces_dep_") as directory:
            base = Path(directory)
            (base / "requirements.txt").write_text("streamlit==1.67.0\n", encoding="utf-8")
            binary = base / "bin"
            binary.mkdir()
            python = binary / "python3"
            calls = base / "calls.txt"
            python.write_text(
                '#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALLS_FILE"\nexit 0\n',
                encoding="utf-8"
            )
            python.chmod(0o755)
            env = dict(os.environ)
            env["PATH"] = str(binary) + os.pathsep + env.get("PATH", "")
            env["CALLS_FILE"] = str(calls)
            result = subprocess.run(
                ["bash", "-c", update_command()], cwd=base, env=env,
                capture_output=True, text=True, timeout=15
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                calls.read_text(encoding="utf-8").splitlines(),
                ["-m pip install --user -r requirements.txt"]
            )
            python.write_text("#!/bin/sh\nexit 17\n", encoding="utf-8")
            python.chmod(0o755)
            failed = subprocess.run(
                ["bash", "-c", update_command()], cwd=base, env=env,
                capture_output=True, text=True, timeout=15
            )
            self.assertEqual(failed.returncode, 17, failed.stderr)


if __name__ == "__main__":
    unittest.main()
