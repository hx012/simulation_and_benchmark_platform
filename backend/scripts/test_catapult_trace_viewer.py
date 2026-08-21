from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.common.config import Settings  # noqa: E402
from app.simulation.catapult_trace_exporter import (  # noqa: E402
    CatapultTraceExporter,
)
from app.simulation.task_io_service import SimulationTaskIOService  # noqa: E402


class CatapultTraceViewerTest(unittest.TestCase):
    def test_export_and_locate_viewer(self) -> None:
        catapult_home = PROJECT_ROOT / "tools" / "catapult"
        if not catapult_home.is_dir():
            self.skipTest(f"Catapult checkout is not available: {catapult_home}")

        with tempfile.TemporaryDirectory() as temp_dir:
            task_root = Path(temp_dir).resolve()
            workspace = task_root / "SIM-CATAPULT-TEST"
            trace_path = (
                workspace / "result" / "trace" / "dumps" / "trace.json"
            )
            trace_path.parent.mkdir(parents=True)
            trace_path.write_text(
                json.dumps(
                    [
                        {
                            "name": "unit-test-event",
                            "ph": "X",
                            "pid": 1,
                            "tid": 1,
                            "ts": 0,
                            "dur": 10,
                        }
                    ]
                ),
                encoding="utf-8",
            )

            settings = Settings(
                task_root=task_root,
                catapult_home=catapult_home,
                catapult_python=Path(sys.executable),
                sim_trace_viewer_config="full",
                sim_trace_viewer_timeout_seconds=60,
            )
            result = CatapultTraceExporter(settings).run(
                str(workspace),
                title="Catapult Export Test",
            )

            self.assertTrue(result.success, result.error_message)
            self.assertIsNotNone(result.trace_html_path)
            assert result.trace_html_path is not None
            self.assertGreater(result.trace_html_path.stat().st_size, 0)
            viewer_html = result.trace_html_path.read_text(encoding="utf-8")
            self.assertIn('<script id="viewer-data"', viewer_html)
            self.assertIn('id="platform-catapult-integration"', viewer_html)
            self.assertIn('catapult-trace-viewer-status', viewer_html)

            task = SimpleNamespace(workspace_path=str(workspace))
            io_service = SimulationTaskIOService(settings)
            artifacts = io_service.read_result_artifacts(task)  # type: ignore[arg-type]
            self.assertTrue(artifacts.trace_source_available)
            self.assertTrue(artifacts.trace_viewer_available)
            self.assertEqual(
                io_service.get_trace_viewer_path(task),  # type: ignore[arg-type]
                result.trace_html_path,
            )

    def test_rejects_workspace_outside_task_root(self) -> None:
        with tempfile.TemporaryDirectory() as task_dir:
            with tempfile.TemporaryDirectory() as outside_dir:
                settings = Settings(
                    task_root=Path(task_dir),
                    catapult_home=PROJECT_ROOT / "tools" / "catapult",
                )
                result = CatapultTraceExporter(settings).run(
                    outside_dir,
                    title="Outside",
                )

        self.assertFalse(result.success)
        self.assertIn("outside TASK_ROOT", result.error_message or "")


if __name__ == "__main__":
    unittest.main()
