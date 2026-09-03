"""Unit tests for Phase 5 Repository Intelligence & Scanner."""

import json
import os
import shutil
import tempfile
import unittest

from app.context.scanner import RepositoryScanner


class TestRepositoryScanner(unittest.TestCase):

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="nexforge_scanner_test_")

        # Create dummy project layout
        os.makedirs(os.path.join(self.temp_dir, "src", "core"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, "tests"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, "node_modules", "pkg"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, ".git"), exist_ok=True)

        # Create files
        with open(os.path.join(self.temp_dir, "src", "main.py"), "w", encoding="utf-8") as f:
            f.write("def start():\n    print('Starting server')\n\nif __name__ == '__main__':\n    start()\n")

        with open(os.path.join(self.temp_dir, "src", "core", "utils.py"), "w", encoding="utf-8") as f:
            f.write("def helper(x: int) -> int:\n    return x * 2\n")

        with open(os.path.join(self.temp_dir, "tests", "test_main.py"), "w", encoding="utf-8") as f:
            f.write("import unittest\n\nclass TestMain(unittest.TestCase):\n    def test_start(self):\n        self.assertTrue(True)\n")

        with open(os.path.join(self.temp_dir, "requirements.txt"), "w", encoding="utf-8") as f:
            f.write("fastapi>=0.100.0\npydantic>=2.0\npytest==7.4.0\n# comment\n")

        with open(os.path.join(self.temp_dir, "package.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "name": "mock-app",
                "dependencies": {
                    "react": "^18.2.0",
                    "lucide-react": "^0.300.0"
                },
                "devDependencies": {
                    "vite": "^5.0.0"
                }
            }))

        # Ignored files
        with open(os.path.join(self.temp_dir, "node_modules", "pkg", "ignored.js"), "w", encoding="utf-8") as f:
            f.write("console.log('should be ignored');")

        with open(os.path.join(self.temp_dir, ".git", "config"), "w", encoding="utf-8") as f:
            f.write("dummy git config")

    def tearDown(self) -> None:
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_scanner_discovers_structure_and_ignores(self) -> None:
        scanner = RepositoryScanner(self.temp_dir)
        summary = scanner.scan()

        self.assertGreaterEqual(summary.total_files, 4)
        self.assertIn("Python", summary.languages)
        self.assertIn("JSON", summary.languages)

        # Check ignored paths
        rel_paths = [f.relative_path.replace("\\", "/") for f in summary.files]
        self.assertNotIn("node_modules/pkg/ignored.js", rel_paths)
        self.assertNotIn(".git/config", rel_paths)

    def test_entry_point_and_test_detection(self) -> None:
        scanner = RepositoryScanner(self.temp_dir)
        summary = scanner.scan()

        rel_paths = [f.relative_path.replace("\\", "/") for f in summary.files]
        self.assertIn("src/main.py", summary.entry_points)
        self.assertIn("unittest/pytest", summary.test_frameworks)

        test_files = [f.relative_path.replace("\\", "/") for f in summary.files if f.is_test]
        self.assertIn("tests/test_main.py", test_files)

    def test_manifest_parsing_and_framework_inference(self) -> None:
        scanner = RepositoryScanner(self.temp_dir)
        summary = scanner.scan()

        self.assertEqual(len(summary.manifests), 2)
        manifest_types = [m.manifest_type for m in summary.manifests]
        self.assertIn("requirements.txt", manifest_types)
        self.assertIn("package.json", manifest_types)

        # Framework inference
        self.assertIn("FastAPI", summary.frameworks)
        self.assertIn("Pydantic", summary.frameworks)
        self.assertIn("Pytest", summary.frameworks)
        self.assertIn("React", summary.frameworks)
        self.assertIn("Vite", summary.frameworks)


if __name__ == "__main__":
    unittest.main()
