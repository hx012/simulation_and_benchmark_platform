import unittest

from chip_performance_analysis.trace_time import (
    TraceAnalysisError,
    TraceProducer,
    analyze_trace,
    normalize_trace_json,
)


class TraceTimeAnalysisTests(unittest.TestCase):
    def test_mskpp_merges_overlapping_intervals_and_skips_sync(self) -> None:
        events = [
            {"tid": 1, "ts": 0, "args": {"name": "VECTOR"}},
            {"tid": 2, "ts": 0, "args": {"name": "MTE2"}},
            {"tid": 1, "ts": 10, "dur": 5, "name": "op-a"},
            {"tid": 1, "ts": 12, "dur": 5, "name": "op-b"},
            {"tid": 1, "ts": 18, "dur": 4, "name": "WAIT_FLAG"},
            {"tid": 2, "ts": 11, "dur": 3, "name": "dma"},
        ]

        result = analyze_trace(events, TraceProducer.MSKPP)

        self.assertEqual(result.producer, TraceProducer.MSKPP)
        self.assertEqual(result.total_cycles, 12)
        self.assertEqual(result.sync_event_count, 1)
        self.assertEqual(result.analyzed_event_count, 3)
        self.assertEqual(
            {item.name: item.cycles for item in result.items},
            {"VECTOR": 7.0, "MTE2": 3.0},
        )

    def test_esl_groups_core_subcore_and_applies_cycle_scale(self) -> None:
        events = [
            {"tid": "A", "pid": "0.0", "ts": 0.0, "dur": 1.0, "name": "op-a"},
            {"tid": "A", "pid": "0.0", "ts": 0.5, "dur": 1.0, "name": "op-b"},
            {"tid": "A", "pid": "0.0", "ts": 0.7, "dur": 0.1, "name": "waitFlag"},
        ]

        result = analyze_trace(events, TraceProducer.ESL)

        self.assertEqual(result.producer, TraceProducer.ESL)
        self.assertEqual(result.total_cycles, 2475.0)
        self.assertEqual(result.items[0].cycles, 2475.0)
        self.assertEqual(result.sync_event_count, 1)

    def test_rejects_selected_producer_when_shape_does_not_match(self) -> None:
        with self.assertRaises(TraceAnalysisError):
            analyze_trace(
                [{"tid": 1, "pid": "0.0", "ts": 0, "dur": 1}],
                TraceProducer.MSKPP,
            )

    def test_normalizes_wrapped_trace_events(self) -> None:
        events = normalize_trace_json({"traceEvents": [{"name": "x"}]})
        self.assertEqual(events, [{"name": "x"}])


if __name__ == "__main__":
    unittest.main()
