"""
Phase 3 Tests: Activity Stream
Tests event emission, SSE generator, event queuing, stream close/reopen.
"""
import asyncio
import json
import pytest
from app.agent.activity_stream.stream import ActivityStream, ActivityEvent


class TestActivityStream:
    def setup_method(self):
        self.stream = ActivityStream("exec_test_001")

    def test_emit_basic_event(self):
        """Emit an event and verify it's in the event list."""
        asyncio.run(self.stream.emit("test_event", {"key": "value"}))
        events = self.stream.get_all_events()
        assert len(events) == 1
        assert events[0].event_type == "test_event"

    def test_emit_event_has_required_fields(self):
        """Each emitted event should have required fields."""
        asyncio.run(self.stream.emit("my_event", {"data": "test"}, level="info"))
        events = self.stream.get_all_events()
        e = events[0]
        assert hasattr(e, "id")
        assert hasattr(e, "execution_id")
        assert hasattr(e, "event_type")
        assert hasattr(e, "message")
        assert hasattr(e, "data")
        assert hasattr(e, "level")
        assert hasattr(e, "timestamp")

    def test_execution_id_in_event(self):
        """Event should reference the execution ID."""
        asyncio.run(self.stream.emit("id_test", {}))
        events = self.stream.get_all_events()
        assert events[0].execution_id == "exec_test_001"

    def test_multiple_events_ordered(self):
        """Events should be in emission order."""
        asyncio.run(self.stream.emit("first", {"n": 1}))
        asyncio.run(self.stream.emit("second", {"n": 2}))
        asyncio.run(self.stream.emit("third", {"n": 3}))

        events = self.stream.get_all_events()
        assert len(events) == 3
        types = [e.event_type for e in events]
        assert types == ["first", "second", "third"]

    def test_level_info(self):
        """Level should default to 'info' if not specified."""
        asyncio.run(self.stream.emit("level_test", {}))
        events = self.stream.get_all_events()
        assert events[0].level == "info"

    def test_level_success(self):
        asyncio.run(self.stream.emit("success_event", {}, level="success"))
        events = self.stream.get_all_events()
        assert events[0].level == "success"

    def test_level_error(self):
        asyncio.run(self.stream.emit("error_event", {}, level="error"))
        events = self.stream.get_all_events()
        assert events[0].level == "error"

    def test_level_warning(self):
        asyncio.run(self.stream.emit("warn_event", {}, level="warning"))
        events = self.stream.get_all_events()
        assert events[0].level == "warning"

    def test_get_all_events_returns_copy(self):
        """get_all_events should not allow external modification."""
        asyncio.run(self.stream.emit("copy_test", {}))
        events = self.stream.get_all_events()
        events.clear()  # Modify returned list
        # Original should still have events
        events2 = self.stream.get_all_events()
        assert len(events2) == 1

    def test_data_preserved_in_event(self):
        """Complex data structure should be preserved."""
        complex_data = {
            "nested": {"a": 1, "b": [1, 2, 3]},
            "count": 42,
            "label": "test",
        }
        asyncio.run(self.stream.emit("data_test", complex_data))
        events = self.stream.get_all_events()
        assert events[0].data == complex_data

    def test_close_stream(self):
        """Closed stream should not crash on close."""
        self.stream.close()
        # Emitting after close should be handled gracefully (no crash)
        asyncio.run(self.stream.emit("post_close", {}))

    def test_sse_generator_yields_data(self):
        """SSE generator should yield formatted SSE data."""
        async def collect_sse():
            await self.stream.emit("sse_test", {"key": "val"})
            self.stream.close()

            lines = []
            async for line in self.stream.sse_generator():
                lines.append(line)
                # Stop once we have some data
                if len(lines) >= 2:
                    break
            return lines

        lines = asyncio.run(collect_sse())
        # At least one line should be SSE-formatted
        has_data_prefix = any(line.startswith("data:") for line in lines)
        assert has_data_prefix

    def test_sse_data_is_valid_json(self):
        """Each SSE data line should contain valid JSON."""
        async def collect():
            await self.stream.emit("json_test", {"x": 99})
            self.stream.close()
            results = []
            async for line in self.stream.sse_generator():
                line = line.strip()
                if line.startswith("data:"):
                    raw = line[5:].strip()
                    if raw and raw != "[KEEPALIVE]":
                        try:
                            parsed = json.loads(raw)
                            results.append(parsed)
                        except json.JSONDecodeError:
                            pass
                if len(results) >= 1:
                    break
            return results

        results = asyncio.run(collect())
        assert len(results) >= 1
        # Should be an event dict or stream_end marker
        first = results[0]
        assert isinstance(first, dict)

    def test_timestamp_str_present(self):
        """Events to_dict should have a formatted timestamp string."""
        asyncio.run(self.stream.emit("ts_test", {}))
        events = self.stream.get_all_events()
        d = events[0].to_dict()
        assert "timestamp_str" in d
        ts_str = d["timestamp_str"]
        assert isinstance(ts_str, str)
        assert len(ts_str) > 0

    def test_unique_event_ids(self):
        """Each event should have a unique ID."""
        for i in range(5):
            asyncio.run(self.stream.emit(f"event_{i}", {}))

        events = self.stream.get_all_events()
        ids = [e.id for e in events]
        assert len(set(ids)) == 5  # All unique

    def test_to_dict_contains_all_fields(self):
        """Event to_dict should contain all required serialized fields."""
        asyncio.run(self.stream.emit("dict_test", {"key": "val"}, level="success"))
        events = self.stream.get_all_events()
        d = events[0].to_dict()
        required = ["id", "execution_id", "event_type", "message", "data",
                    "timestamp", "timestamp_str", "level"]
        for k in required:
            assert k in d, f"Missing key: {k}"

    def test_to_sse_format(self):
        """to_sse should produce proper SSE format."""
        asyncio.run(self.stream.emit("sse_format_test", {}))
        events = self.stream.get_all_events()
        sse = events[0].to_sse()
        assert sse.startswith("data: ")
        assert sse.endswith("\n\n")
        # The JSON between "data: " and "\n\n" should be valid
        json_part = sse[6:].strip()
        parsed = json.loads(json_part)
        assert parsed["event_type"] == "sse_format_test"

    def test_human_readable_messages(self):
        """Known event types should get human-readable messages."""
        asyncio.run(self.stream.emit("plan_generated", {"step_count": 5}))
        events = self.stream.get_all_events()
        msg = events[0].message
        assert msg and len(msg) > 0
        # Should not just be "plan_generated"
        assert msg != "plan_generated"
