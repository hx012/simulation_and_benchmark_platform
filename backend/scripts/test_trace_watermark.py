from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.simulation.trace_watermark import (  # noqa: E402
    WATERMARK_LAYER_ID,
    iter_watermarked_trace_html,
)


class TraceWatermarkTests(unittest.TestCase):
    def test_injects_employee_watermark_after_body_tag(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            viewer = Path(temporary_directory) / "trace.html"
            viewer.write_text(
                '<html><head><script>const value = "large";</script></head>'
                '<body class="viewer"><main>Trace</main></body></html>',
                encoding="utf-8",
            )

            rendered = b"".join(iter_watermarked_trace_html(
                viewer,
                "E123456",
                chunk_size=7,
            )).decode("utf-8")

            body_tag = '<body class="viewer">'
            self.assertIn(body_tag, rendered)
            self.assertIn(f'id="{WATERMARK_LAYER_ID}"', rendered)
            self.assertIn("MSKPP&amp;AIBench + E123456", rendered)
            self.assertIn('font: 400 15px/1.2 Arial, "Microsoft YaHei", sans-serif;', rendered)
            self.assertLess(
                rendered.index(body_tag),
                rendered.index(f'id="{WATERMARK_LAYER_ID}"'),
            )
            self.assertIn("<main>Trace</main>", rendered)

    def test_escapes_employee_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            viewer = Path(temporary_directory) / "trace.html"
            viewer.write_text("<html><body>Trace</body></html>", encoding="utf-8")

            rendered = b"".join(iter_watermarked_trace_html(
                viewer,
                '<script>alert("x")</script>',
            )).decode("utf-8")

            self.assertNotIn('<script>alert("x")</script>', rendered)
            self.assertIn("&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;", rendered)


if __name__ == "__main__":
    unittest.main()
