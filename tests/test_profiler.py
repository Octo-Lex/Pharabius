from __future__ import annotations

import json
from pathlib import Path

from pharabius.core.init_workspace import initialize_workspace
from pharabius.core.profiler import profile_repository, write_repository_profile


def test_profile_repository_detects_typescript_project(tmp_path: Path) -> None:
    (tmp_path / "src" / "auth").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    (tmp_path / ".github" / "workflows").mkdir(parents=True)

    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "main": "src/index.ts",
                "scripts": {
                    "test": "jest",
                    "build": "vite build",
                },
                "dependencies": {
                    "react": "^18.0.0",
                    "next": "^14.0.0",
                },
                "devDependencies": {
                    "typescript": "^5.0.0",
                    "jest": "^29.0.0",
                    "vite": "^5.0.0",
                },
            }
        ),
        encoding="utf-8",
    )

    (tmp_path / "src" / "index.ts").write_text("export const app = true;\n", encoding="utf-8")
    (tmp_path / "src" / "auth" / "session.ts").write_text(
        "export const token = '';\n", encoding="utf-8"
    )
    (tmp_path / "tests" / "app.test.ts").write_text("test('works', () => {});\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Example\n", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM node:20\n", encoding="utf-8")
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    (tmp_path / "tsconfig.json").write_text("{}", encoding="utf-8")

    profile = profile_repository(tmp_path)

    assert profile.project_name == tmp_path.name
    assert "TypeScript" in profile.detected_languages
    assert "npm" in profile.package_managers
    assert "React" in profile.detected_frameworks
    assert "Next.js" in profile.detected_frameworks
    assert "Jest" in profile.test_frameworks
    assert "Vite" in profile.build_tools
    assert "src/index.ts" in profile.entry_points
    assert "tests" in profile.test_directories
    assert "README.md" in profile.documentation_files
    assert "Dockerfile" in profile.deployment_files
    assert ".github/workflows/ci.yml" in profile.deployment_files
    assert "tsconfig.json" in profile.configuration_files
    assert "src/auth/session.ts" in profile.risk_sensitive_areas
    assert profile.analysis_confidence == "High"


def test_write_repository_profile_writes_project_profile_json(tmp_path: Path) -> None:
    initialize_workspace(tmp_path)

    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("fastapi\npytest\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()

    profile = write_repository_profile(tmp_path)

    output_path = tmp_path / ".ai-debt" / "project-profile.json"
    written = json.loads(output_path.read_text(encoding="utf-8"))

    assert output_path.exists()
    assert profile.project_name == tmp_path.name
    assert written["project_name"] == tmp_path.name
    assert "Python" in written["detected_languages"]
    assert "pip" in written["package_managers"]
    assert "FastAPI" in written["detected_frameworks"]
    assert "pytest" in written["test_frameworks"]
