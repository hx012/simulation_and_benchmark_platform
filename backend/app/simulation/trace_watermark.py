from __future__ import annotations

from collections.abc import Iterator
from html import escape
from pathlib import Path


WATERMARK_LAYER_ID = "platform-trace-watermark"
_SEARCH_TAIL_BYTES = 1024


def build_trace_watermark_markup(employee_id: str) -> bytes:
    content = escape(
        f"MSKPP&AIBench + {employee_id}",
        quote=True,
    )
    marks = "".join(f"<span>{content}</span>" for _ in range(48))
    return f"""
<style id="platform-trace-watermark-style">
  #{WATERMARK_LAYER_ID} {{
    position: fixed;
    inset: 0;
    z-index: 2147483647;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
    grid-auto-rows: 112px;
    align-items: center;
    justify-items: center;
    overflow: hidden;
    pointer-events: none;
    user-select: none;
  }}
  #{WATERMARK_LAYER_ID} span {{
    color: rgba(31, 78, 121, 0.10);
    font: 400 15px/1.2 Arial, "Microsoft YaHei", sans-serif;
    white-space: nowrap;
    transform: rotate(-22deg);
  }}
</style>
<div id="{WATERMARK_LAYER_ID}" aria-hidden="true">{marks}</div>
""".encode("utf-8")


def iter_watermarked_trace_html(
    path: Path,
    employee_id: str,
    *,
    chunk_size: int = 64 * 1024,
) -> Iterator[bytes]:
    """Stream a self-contained Catapult viewer with a per-request watermark."""
    watermark = build_trace_watermark_markup(employee_id)
    pending = b""
    inserted = False

    with path.open("rb") as source:
        while chunk := source.read(chunk_size):
            if inserted:
                yield chunk
                continue

            pending += chunk
            lower_pending = pending.lower()
            body_start = lower_pending.find(b"<body")

            if body_start < 0:
                if len(pending) > _SEARCH_TAIL_BYTES:
                    yield pending[:-_SEARCH_TAIL_BYTES]
                    pending = pending[-_SEARCH_TAIL_BYTES:]
                continue

            body_end = lower_pending.find(b">", body_start)
            if body_end < 0:
                if body_start > 0:
                    yield pending[:body_start]
                    pending = pending[body_start:]
                continue

            yield pending[:body_end + 1]
            yield watermark
            yield pending[body_end + 1:]
            pending = b""
            inserted = True

    if pending:
        yield pending
