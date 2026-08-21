"""Python 3 entrypoint for Catapult's trace2html implementation.

Catapult's checked-in executable still has a Python 2.7 shebang.  This small
adapter deliberately keeps all Catapult imports in a subprocess and works
around the vendored six module on newer Python versions without modifying the
third-party source tree.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import types
from pathlib import Path


PLATFORM_INTEGRATION_MARKER = 'id="platform-catapult-integration"'
PLATFORM_INTEGRATION = r"""
<style id="platform-catapult-integration">
  html.platform-trace-importing body > .overlay {
    display: none !important;
  }
</style>
<script>
(function() {
  'use strict';

  const messageType = 'catapult-trace-viewer-status';
  const root = document.documentElement;
  root.classList.add('platform-trace-importing');

  function notifyPlatform(status) {
    if (window.parent !== window) {
      window.parent.postMessage({type: messageType, status: status}, '*');
    }
  }

  notifyPlatform('importing');

  document.addEventListener('DOMContentLoaded', function() {
    const startedAt = Date.now();
    const timer = window.setInterval(function() {
      const timeline = document.querySelector('tr-ui-timeline-view');
      const importFailed = Array.prototype.some.call(
          document.querySelectorAll('.overlay'),
          function(overlay) {
            return overlay.visible && overlay.title === 'Import error';
          });

      let status = null;
      if (timeline && timeline.model) {
        status = 'ready';
      } else if (importFailed) {
        status = 'error';
      } else if (Date.now() - startedAt >= 120000) {
        status = 'timeout';
      }

      if (status === null) return;

      window.clearInterval(timer);
      root.classList.remove('platform-trace-importing');
      notifyPlatform(status);
    }, 50);
  });
})();
</script>
"""


def inject_platform_integration(output_path: Path) -> None:
    html = output_path.read_text(encoding="utf-8")
    if PLATFORM_INTEGRATION_MARKER in html:
        return

    closing_head = html.rfind("</head>")
    if closing_head < 0:
        raise RuntimeError("Catapult output does not contain a closing head tag")

    integrated_html = (
        html[:closing_head]
        + PLATFORM_INTEGRATION
        + "\n"
        + html[closing_head:]
    )
    output_path.write_text(integrated_html, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catapult-root", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--config",
        default="full",
        choices=("chrome", "full", "lean", "systrace", "v8"),
    )
    parser.add_argument("--title", default="Simulation Trace")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    catapult_root = args.catapult_root.resolve()
    tracing_root = catapult_root / "tracing"
    vendored_six = catapult_root / "third_party" / "six"
    if not (tracing_root / "tracing_build" / "trace2html.py").is_file():
        raise FileNotFoundError(
            f"Catapult trace2html was not found under {catapult_root}"
        )

    # Python 3.14 no longer consults the legacy find_module hook used by
    # Catapult's vendored six 1.15. Add the equivalent PEP 451 hook at runtime
    # so six.moves remains importable without editing third-party sources.
    sys.path.insert(0, str(vendored_six))
    import six  # type: ignore[import-not-found]  # noqa: PLC0415

    if not hasattr(six._importer, "find_spec"):
        def find_spec(
            importer: object,
            fullname: str,
            path: object = None,
            target: object = None,
        ) -> object:
            del path, target
            if fullname in importer.known_modules:  # type: ignore[attr-defined]
                return importlib.util.spec_from_loader(fullname, importer)
            return None

        six._importer.find_spec = types.MethodType(  # type: ignore[attr-defined]
            find_spec,
            six._importer,
        )

    sys.path.insert(0, str(tracing_root))

    from tracing_build import trace2html  # type: ignore[import-not-found]  # noqa: PLC0415

    output_path = args.output.resolve()
    exit_code = trace2html.Main(
        [
            "trace2html",
            "--quiet",
            "--config",
            args.config,
            "--title",
            args.title,
            "--output",
            str(output_path),
            str(args.input.resolve()),
        ]
    )
    if exit_code == 0:
        inject_platform_integration(output_path)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
