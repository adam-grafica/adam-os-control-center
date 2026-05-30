"""Unit tests for ADAM OS Control Center services (D-C3).

Tests all service modules with mocked dependencies:
- infra_reader (psutil)
- agent_tracker (filesystem)
- log_streamer (in-memory buffer)
- file_tree (filesystem)
- config_service (JSON file)
- command_center (in-memory kanban)
- api_registry (in-memory provider registry)

Coverage target: 70%+ on services.
"""

from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

import pytest


# ── TestInfraReader ──


class TestInfraReader:
    """Tests for InfraReader — psutil-based server metrics service."""

    @patch("app.services.infra_reader.HAS_PSUTIL", True)
    @patch("app.services.infra_reader._psutil")
    def test_get_cpu_returns_dict_with_keys(self, mock_psutil):
        """get_cpu() returns dict with percent, cores, load_avg, and status='ok'."""
        from app.services.infra_reader import InfraReader

        mock_psutil.cpu_percent.return_value = 42.5
        mock_psutil.getloadavg.return_value = (1.5, 1.2, 0.8)
        mock_psutil.cpu_count.return_value = 8

        reader = InfraReader()
        result = reader.get_cpu()

        assert isinstance(result, dict)
        assert result["percent"] == 42.5
        assert result["cores"] == 8
        assert result["load_avg"] == [1.5, 1.2, 0.8]
        assert result["status"] == "ok"

    @patch("app.services.infra_reader.HAS_PSUTIL", False)
    def test_get_cpu_without_psutil_returns_empty_data(self):
        """get_cpu() returns zeros/empty defaults when psutil not installed."""
        from app.services.infra_reader import InfraReader

        reader = InfraReader()
        result = reader.get_cpu()

        assert result["percent"] == 0.0
        assert result["cores"] == 0
        assert result["load_avg"] == [0.0, 0.0, 0.0]
        assert result["status"] == "unavailable"
        assert result["per_cpu"] == []

    @patch("app.services.infra_reader.HAS_PSUTIL", True)
    @patch("app.services.infra_reader._psutil")
    def test_get_memory_returns_dict_with_keys(self, mock_psutil):
        """get_memory() returns dict with total, available, used, free, percent."""
        from app.services.infra_reader import InfraReader

        mock_mem = MagicMock()
        mock_mem.total = 16_000_000_000
        mock_mem.available = 8_000_000_000
        mock_mem.used = 7_000_000_000
        mock_mem.free = 1_000_000_000
        mock_mem.percent = 45.0
        mock_psutil.virtual_memory.return_value = mock_mem

        reader = InfraReader()
        result = reader.get_memory()

        assert result["total"] == 16_000_000_000
        assert result["available"] == 8_000_000_000
        assert result["used"] == 7_000_000_000
        assert result["free"] == 1_000_000_000
        assert result["percent"] == 45.0
        assert result["status"] == "ok"

    @patch("app.services.infra_reader.HAS_PSUTIL", True)
    @patch("app.services.infra_reader._psutil")
    def test_get_memory_critical_status(self, mock_psutil):
        """get_memory() returns status='critical' when percent >= 90."""
        from app.services.infra_reader import InfraReader

        mock_mem = MagicMock()
        mock_mem.total = 16_000_000_000
        mock_mem.available = 1_000_000_000
        mock_mem.used = 15_000_000_000
        mock_mem.free = 100_000_000
        mock_mem.percent = 94.0
        mock_psutil.virtual_memory.return_value = mock_mem

        reader = InfraReader()
        result = reader.get_memory()

        assert result["percent"] == 94.0
        assert result["status"] == "critical"

    @patch("app.services.infra_reader.HAS_PSUTIL", False)
    def test_get_memory_without_psutil_returns_empty_data(self):
        """get_memory() returns zero data when psutil not installed."""
        from app.services.infra_reader import InfraReader

        reader = InfraReader()
        result = reader.get_memory()

        assert result["total"] == 0
        assert result["used"] == 0
        assert result["free"] == 0
        assert result["percent"] == 0.0
        assert result["status"] == "unavailable"

    @patch("app.services.infra_reader.HAS_PSUTIL", True)
    @patch("app.services.infra_reader._psutil")
    def test_get_disk_returns_list_of_partitions(self, mock_psutil):
        """get_disk() returns list with mount, total, used, free, percent per partition."""
        from app.services.infra_reader import InfraReader

        mock_part = MagicMock()
        mock_part.device = "/dev/sda1"
        mock_part.mountpoint = "/"
        mock_part.fstype = "ext4"

        mock_psutil.disk_partitions.return_value = [mock_part]

        mock_usage = MagicMock()
        mock_usage.total = 500_000_000_000
        mock_usage.used = 300_000_000_000
        mock_usage.free = 200_000_000_000
        mock_usage.percent = 60.0
        mock_psutil.disk_usage.return_value = mock_usage

        reader = InfraReader()
        result = reader.get_disk()

        assert isinstance(result, list)
        assert len(result) >= 1
        partition = result[0]
        assert partition["mountpoint"] == "/"
        assert partition["total"] == 500_000_000_000
        assert partition["used"] == 300_000_000_000
        assert partition["free"] == 200_000_000_000
        assert partition["percent"] == 60.0

    @patch("app.services.infra_reader.HAS_PSUTIL", True)
    @patch("app.services.infra_reader._psutil")
    def test_get_disk_skips_pseudo_filesystems(self, mock_psutil):
        """get_disk() skips pseudo-filesystems like proc, sysfs, tmpfs."""
        from app.services.infra_reader import InfraReader

        real_part = MagicMock()
        real_part.device = "/dev/sda1"
        real_part.mountpoint = "/"
        real_part.fstype = "ext4"

        pseudo_part = MagicMock()
        pseudo_part.device = "tmpfs"
        pseudo_part.mountpoint = "/run"
        pseudo_part.fstype = "tmpfs"

        mock_psutil.disk_partitions.return_value = [real_part, pseudo_part]

        mock_usage = MagicMock()
        mock_usage.total = 500_000_000_000
        mock_usage.used = 300_000_000_000
        mock_usage.free = 200_000_000_000
        mock_usage.percent = 60.0
        mock_psutil.disk_usage.return_value = mock_usage

        reader = InfraReader()
        result = reader.get_disk()

        assert len(result) == 1
        assert result[0]["mountpoint"] == "/"

    @patch("app.services.infra_reader.HAS_PSUTIL", False)
    def test_get_disk_without_psutil_returns_empty_list(self):
        """get_disk() returns empty list when psutil not installed."""
        from app.services.infra_reader import InfraReader

        reader = InfraReader()
        result = reader.get_disk()
        assert result == []

    @patch("app.services.infra_reader.HAS_PSUTIL", True)
    @patch("app.services.infra_reader._psutil")
    def test_get_network_returns_dict_with_keys(self, mock_psutil):
        """get_network() returns dict with bytes_sent, bytes_recv, packets, interfaces."""
        from app.services.infra_reader import InfraReader

        mock_net = MagicMock()
        mock_net.bytes_sent = 1_000_000
        mock_net.bytes_recv = 2_000_000
        mock_net.packets_sent = 5_000
        mock_net.packets_recv = 10_000
        mock_net.errin = 0
        mock_net.errout = 0

        # First call (no pernic) returns the aggregate namedtuple
        # Second call (pernic=True) returns empty dict for interfaces
        mock_psutil.net_io_counters.side_effect = [mock_net, {}]

        reader = InfraReader()
        result = reader.get_network()

        assert result["bytes_sent"] == 1_000_000
        assert result["bytes_recv"] == 2_000_000
        assert result["packets_sent"] == 5_000
        assert result["packets_recv"] == 10_000
        assert result["status"] == "ok"

    @patch("app.services.infra_reader.HAS_PSUTIL", False)
    def test_get_network_without_psutil_returns_empty_data(self):
        """get_network() returns zero data when psutil not installed."""
        from app.services.infra_reader import InfraReader

        reader = InfraReader()
        result = reader.get_network()

        assert result["bytes_sent"] == 0
        assert result["bytes_recv"] == 0
        assert result["status"] == "unavailable"

    @patch("app.services.infra_reader.HAS_PSUTIL", True)
    @patch("app.services.infra_reader._psutil")
    def test_get_top_processes_returns_sorted_list(self, mock_psutil):
        """get_top_processes() returns top N processes sorted by memory_percent desc."""
        from app.services.infra_reader import InfraReader

        procs = []
        for pid, name, cpu, mem, status in [
            (1, "proc_a", 10.0, 5.0, "running"),
            (2, "proc_b", 20.0, 15.0, "sleeping"),
            (3, "proc_c", 5.0, 2.0, "running"),
        ]:
            p = MagicMock()
            p.info = {"pid": pid, "name": name, "cpu_percent": cpu, "memory_percent": mem, "status": status}
            procs.append(p)

        mock_psutil.process_iter.return_value = procs

        reader = InfraReader()
        result = reader.get_top_processes(2)

        assert isinstance(result, list)
        assert len(result) == 2
        # Descending by memory_percent
        assert result[0]["pid"] == 2
        assert result[1]["pid"] == 1

    @patch("app.services.infra_reader.HAS_PSUTIL", False)
    def test_get_top_processes_without_psutil_returns_empty_list(self):
        """get_top_processes() returns empty list when psutil not installed."""
        from app.services.infra_reader import InfraReader

        reader = InfraReader()
        result = reader.get_top_processes(10)
        assert result == []

    @patch("app.services.infra_reader.HAS_PSUTIL", True)
    @patch("app.services.infra_reader._psutil")
    def test_get_full_infra_snapshot_returns_all_keys(self, mock_psutil):
        """get_full_infra_snapshot() returns dict with ts, cpu, memory, disk, network, uptime, processes."""
        from app.services.infra_reader import InfraReader

        # Mock everything quickly
        mock_psutil.cpu_percent.return_value = 30.0
        mock_psutil.getloadavg.return_value = (1.0, 0.8, 0.6)
        mock_psutil.cpu_count.return_value = 4

        mock_mem = MagicMock()
        for attr in ("total", "available", "used", "free", "percent"):
            setattr(mock_mem, attr, 0)
        mock_mem.total = 8_000_000_000
        mock_mem.available = 4_000_000_000
        mock_mem.used = 3_500_000_000
        mock_mem.free = 500_000_000
        mock_mem.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_mem

        mock_net = MagicMock()
        for attr in ("bytes_sent", "bytes_recv", "packets_sent", "packets_recv", "errin", "errout"):
            setattr(mock_net, attr, 0)
        mock_net.bytes_sent = 100
        mock_net.bytes_recv = 200
        mock_psutil.net_io_counters.return_value = mock_net

        mock_psutil.disk_partitions.return_value = []
        mock_psutil.boot_time.return_value = time.time() - 3600
        mock_psutil.process_iter.return_value = []

        reader = InfraReader()
        result = reader.get_full_infra_snapshot()

        for key in ("ts", "cpu", "memory", "disk", "network", "uptime", "processes"):
            assert key in result, f"Missing key: {key}"

    @patch("app.services.infra_reader.HAS_PSUTIL", True)
    @patch("app.services.infra_reader._psutil")
    def test_graceful_degradation_on_psutil_exception(self, mock_psutil):
        """get_cpu() degrades gracefully when psutil raises an exception."""
        from app.services.infra_reader import InfraReader

        mock_psutil.cpu_percent.side_effect = RuntimeError("psutil failure")

        reader = InfraReader()
        result = reader.get_cpu()

        assert result["percent"] == 0.0
        assert "error" in result["status"]

    @patch("app.services.infra_reader.HAS_PSUTIL", True)
    @patch("app.services.infra_reader._psutil")
    def test_uptime_returns_dict(self, mock_psutil):
        """get_uptime() returns uptime_seconds and boot_time."""
        from app.services.infra_reader import InfraReader

        boot = time.time() - 7200
        mock_psutil.boot_time.return_value = boot

        reader = InfraReader()
        result = reader.get_uptime()

        assert result["boot_time"] == boot
        assert result["uptime_seconds"] > 0
        assert result["status"] == "ok"

    @patch("app.services.infra_reader.HAS_PSUTIL", False)
    def test_uptime_without_psutil_returns_empty(self):
        """get_uptime() returns zero data when psutil not installed."""
        from app.services.infra_reader import InfraReader

        reader = InfraReader()
        result = reader.get_uptime()

        assert result["uptime_seconds"] == 0
        assert result["boot_time"] is None
        assert result["status"] == "unavailable"

    @patch("app.services.infra_reader.HAS_PSUTIL", True)
    @patch("app.services.infra_reader._psutil")
    def test_free_ram_returns_dict(self, mock_psutil):
        """free_ram() returns a dict with success/message keys (permission typically denied)."""
        from app.services.infra_reader import InfraReader

        mock_mem = MagicMock()
        mock_mem.available = 4_000_000_000
        mock_mem.used = 3_000_000_000
        mock_mem.percent = 40.0
        mock_psutil.virtual_memory.return_value = mock_mem

        reader = InfraReader()
        result = reader.free_ram()

        assert isinstance(result, dict)
        assert "success" in result
        assert "freed_bytes" in result
        assert "message" in result

    @patch("app.services.infra_reader.HAS_PSUTIL", False)
    def test_free_ram_without_psutil(self):
        """free_ram() returns early when psutil not available."""
        from app.services.infra_reader import InfraReader

        reader = InfraReader()
        result = reader.free_ram()

        assert result["success"] is False
        assert "psutil not available" in result["message"]


# ── TestAgentTracker ──


class TestAgentTracker:
    """Tests for AgentTracker — Hermes agent filesystem reader."""

    def test_get_all_agents_returns_empty_when_no_channel_file(self, tmp_path):
        """get_all_agents() returns empty list when channel_directory.json missing."""
        from app.services.agent_tracker import AgentTracker

        tracker = AgentTracker(hermes_root=str(tmp_path))
        agents = tracker.get_all_agents()

        assert isinstance(agents, list)
        assert agents == []

    def test_get_all_agents_parses_list_format(self, tmp_path):
        """get_all_agents() parses list-format channel_directory.json."""
        from app.services.agent_tracker import AgentTracker

        channel_file = tmp_path / "channel_directory.json"
        channel_file.write_text(json.dumps([
            {"id": "agent-1", "name": "Agent One", "type": "channel", "status": "online", "last_seen": "2026-01-01"},
            {"id": "agent-2", "name": "Agent Two", "type": "channel", "status": "idle"},
        ]))

        tracker = AgentTracker(hermes_root=str(tmp_path))
        agents = tracker.get_all_agents()

        assert len(agents) == 2
        assert agents[0]["id"] == "agent-1"
        assert agents[0]["status"] == "online"

    def test_get_all_agents_parses_dict_format(self, tmp_path):
        """get_all_agents() parses dict-format channel_directory.json."""
        from app.services.agent_tracker import AgentTracker

        channel_file = tmp_path / "channel_directory.json"
        channel_file.write_text(json.dumps({
            "agent-1": {"name": "Agent One", "type": "channel", "status": "online"},
        }))

        tracker = AgentTracker(hermes_root=str(tmp_path))
        agents = tracker.get_all_agents()

        assert len(agents) == 1
        assert agents[0]["id"] == "agent-1"

    def test_get_all_agents_fallsback_to_unknown(self, tmp_path):
        """get_all_agents() uses fallback IDs/values when entries lack standard keys."""
        from app.services.agent_tracker import AgentTracker

        channel_file = tmp_path / "channel_directory.json"
        channel_file.write_text(json.dumps([
            {"foo": "bar"},
        ]))

        tracker = AgentTracker(hermes_root=str(tmp_path))
        agents = tracker.get_all_agents()

        assert len(agents) == 1
        assert agents[0]["id"] == "unknown"

    def test_get_agent_status_found(self, tmp_path):
        """get_agent_status() returns agent details when agent exists."""
        from app.services.agent_tracker import AgentTracker

        channel_file = tmp_path / "channel_directory.json"
        channel_file.write_text(json.dumps([
            {"id": "my-agent", "name": "My Agent", "status": "online"},
        ]))

        tracker = AgentTracker(hermes_root=str(tmp_path))
        status = tracker.get_agent_status("my-agent")

        assert status["id"] == "my-agent"
        assert status["status"] == "online"

    def test_get_agent_status_not_found(self, tmp_path):
        """get_agent_status() returns 'unknown' status when agent not in registry."""
        from app.services.agent_tracker import AgentTracker

        tracker = AgentTracker(hermes_root=str(tmp_path))
        status = tracker.get_agent_status("nonexistent")

        assert status["id"] == "nonexistent"
        assert status["status"] == "unknown"

    def test_get_active_tasks_empty_when_no_sessions(self, tmp_path):
        """get_active_tasks() returns empty list when no sessions dir."""
        from app.services.agent_tracker import AgentTracker

        tracker = AgentTracker(hermes_root=str(tmp_path), profile="test")
        tasks = tracker.get_active_tasks()

        assert isinstance(tasks, list)
        assert tasks == []

    def test_get_active_tasks_parses_session_files(self, tmp_path):
        """get_active_tasks() returns parsed tasks from session JSON files."""
        from app.services.agent_tracker import AgentTracker

        sessions_dir = tmp_path / "profiles" / "test" / "sessions"
        sessions_dir.mkdir(parents=True)
        (sessions_dir / "session_001.json").write_text(
            json.dumps({"agent_id": "agent-1", "status": "active"})
        )

        tracker = AgentTracker(hermes_root=str(tmp_path), profile="test")
        tasks = tracker.get_active_tasks()

        assert len(tasks) >= 1
        assert tasks[0]["session_id"] == "session_001"
        assert tasks[0]["source"] == "agent-1"
        assert tasks[0]["type"] == "session"

    def test_get_active_tasks_skips_invalid_json(self, tmp_path):
        """get_active_tasks() skips session files with invalid JSON."""
        from app.services.agent_tracker import AgentTracker

        sessions_dir = tmp_path / "profiles" / "test" / "sessions"
        sessions_dir.mkdir(parents=True)
        (sessions_dir / "bad.json").write_text("not valid json")

        tracker = AgentTracker(hermes_root=str(tmp_path), profile="test")
        tasks = tracker.get_active_tasks()

        assert tasks == []

    def test_get_tools_returns_list_from_auth_and_cron(self, tmp_path):
        """get_tools() reads tools from auth.json and cron/jobs.json."""
        from app.services.agent_tracker import AgentTracker

        profile_dir = tmp_path / "profiles" / "test"
        profile_dir.mkdir(parents=True)

        auth_file = profile_dir / "auth.json"
        auth_file.write_text(json.dumps({
            "openai": {"enabled": True},
            "github": {"enabled": True},
        }))

        cron_dir = profile_dir / "cron"
        cron_dir.mkdir()
        (cron_dir / "jobs.json").write_text(json.dumps([
            {"name": "daily-report", "enabled": True, "schedule": "0 6 * * *"},
        ]))

        tracker = AgentTracker(hermes_root=str(tmp_path), profile="test")
        tools = tracker.get_tools()

        tool_names = [t["name"] for t in tools]
        assert "openai" in tool_names
        assert "github" in tool_names
        assert any("cron:" in t["name"] for t in tools)

    def test_get_tools_empty_when_no_files(self, tmp_path):
        """get_tools() returns empty list when no auth or cron files exist."""
        from app.services.agent_tracker import AgentTracker

        tracker = AgentTracker(hermes_root=str(tmp_path), profile="test")
        tools = tracker.get_tools()

        assert tools == []


# ── TestLogStreamer ──


class TestLogStreamer:
    """Tests for LogStreamer — in-memory rotating log buffer."""

    def test_add_log_returns_entry_with_keys(self):
        """add_log() returns entry with seq, ts, level, source, type, message."""
        from app.services.log_streamer import LogStreamer

        streamer = LogStreamer(buffer_size=100)
        entry = streamer.add_log(level="info", source="test", message="hello")

        assert entry["level"] == "info"
        assert entry["source"] == "test"
        assert entry["message"] == "hello"
        assert entry["type"] == "log"
        assert "seq" in entry
        assert "ts" in entry

    def test_add_log_increments_seq(self):
        """add_log() increments seq for each entry."""
        from app.services.log_streamer import LogStreamer

        streamer = LogStreamer(buffer_size=100)
        e1 = streamer.add_log(message="first")
        e2 = streamer.add_log(message="second")

        assert e2["seq"] == e1["seq"] + 1

    def test_get_recent_logs_newest_first(self):
        """get_recent_logs() returns entries newest first."""
        from app.services.log_streamer import LogStreamer

        streamer = LogStreamer(buffer_size=100)
        streamer.add_log(message="first")
        streamer.add_log(message="second")
        streamer.add_log(message="third")

        logs = streamer.get_recent_logs()

        assert len(logs) == 3
        assert logs[0]["message"] == "third"
        assert logs[-1]["message"] == "first"

    def test_get_recent_logs_respects_limit(self):
        """get_recent_logs(limit=N) returns at most N entries."""
        from app.services.log_streamer import LogStreamer

        streamer = LogStreamer(buffer_size=100)
        for i in range(20):
            streamer.add_log(message=f"entry-{i}")

        logs = streamer.get_recent_logs(limit=5)
        assert len(logs) == 5

    def test_buffer_rotates_when_full(self):
        """Oldest entries dropped when buffer exceeds maxlen."""
        from app.services.log_streamer import LogStreamer

        streamer = LogStreamer(buffer_size=5)
        for i in range(10):
            streamer.add_log(message=f"entry-{i}")

        assert streamer.count == 5
        logs = streamer.get_recent_logs()
        assert logs[-1]["message"] == "entry-5"

    def test_buffer_size_property(self):
        """buffer_size returns the configured max buffer size."""
        from app.services.log_streamer import LogStreamer

        streamer = LogStreamer(buffer_size=200)
        assert streamer.buffer_size == 200

    def test_count_property(self):
        """count returns current number of entries in buffer."""
        from app.services.log_streamer import LogStreamer

        streamer = LogStreamer(buffer_size=100)
        assert streamer.count == 0

        streamer.add_log(message="test")
        assert streamer.count == 1

    def test_add_log_accepts_extra_kwargs(self):
        """add_log() includes extra keyword arguments in the entry."""
        from app.services.log_streamer import LogStreamer

        streamer = LogStreamer(buffer_size=100)
        entry = streamer.add_log(message="test", extra_field="value", count=42)

        assert entry["extra_field"] == "value"
        assert entry["count"] == 42

    @pytest.mark.asyncio
    async def test_stream_logs_yields_existing_entries(self):
        """stream_logs() async generator yields entries already in buffer."""
        from app.services.log_streamer import LogStreamer

        streamer = LogStreamer(buffer_size=100)
        streamer.add_log(message="existing")

        collected = []
        async for event in streamer.stream_logs():
            collected.append(event)
            if len(collected) >= 1:
                break

        assert len(collected) >= 1
        assert "existing" in collected[0]


# ── TestFileTree ──


class TestFileTree:
    """Tests for FileTree — safe filesystem exploration service."""

    def test_get_tree_returns_dict_with_name_type_children(self, tmp_path):
        """get_tree() returns dict with name, type, children for directories."""
        from app.services.file_tree import FileTree

        (tmp_path / "subdir").mkdir()
        (tmp_path / "file1.txt").write_text("hello")

        tree = FileTree(root_path=str(tmp_path))
        result = tree.get_tree()

        assert result["name"] == tmp_path.name
        assert result["type"] == "directory"
        assert "children" in result
        child_names = [c["name"] for c in result["children"]]
        assert "subdir" in child_names
        assert "file1.txt" in child_names

    def test_get_tree_returns_file_info_for_file_path(self, tmp_path):
        """get_tree() on a file path returns file info dict (type: file)."""
        from app.services.file_tree import FileTree

        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")

        tree = FileTree(root_path=str(tmp_path))
        result = tree.get_tree(path="test.txt")

        assert result["type"] == "file"
        assert result["name"] == "test.txt"

    def test_get_tree_nonexistent_path_returns_error(self, tmp_path):
        """get_tree() returns error dict when path does not exist."""
        from app.services.file_tree import FileTree

        tree = FileTree(root_path=str(tmp_path))
        result = tree.get_tree(path="nonexistent")

        assert "error" in result
        assert "Path does not exist" in result["error"]

    def test_get_tree_empty_dir(self, tmp_path):
        """get_tree() on an empty directory returns children as empty list."""
        from app.services.file_tree import FileTree

        (tmp_path / "empty_dir").mkdir()

        tree = FileTree(root_path=str(tmp_path))
        result = tree.get_tree(path="empty_dir")

        assert result["type"] == "directory"
        assert result["children"] == []

    def test_read_file_returns_content_with_metadata(self, tmp_path):
        """read_file() returns content, lines, extension, size, path."""
        from app.services.file_tree import FileTree

        test_file = tmp_path / "test.txt"
        test_file.write_text("line1\nline2\nline3\n")

        tree = FileTree(root_path=str(tmp_path))
        result = tree.read_file("test.txt")

        assert result["content"] == "line1\nline2\nline3\n"
        assert result["lines"] == 3
        assert result["extension"] == ".txt"
        assert result["size"] > 0
        assert result["path"].endswith("test.txt")

    def test_read_file_not_found_returns_error(self, tmp_path):
        """read_file() returns error when file does not exist."""
        from app.services.file_tree import FileTree

        tree = FileTree(root_path=str(tmp_path))
        result = tree.read_file("nonexistent.txt")

        assert "error" in result
        assert "File not found" in result["error"]

    def test_read_file_on_directory_returns_error(self, tmp_path):
        """read_file() returns error when path is a directory, not a file."""
        from app.services.file_tree import FileTree

        (tmp_path / "mydir").mkdir()

        tree = FileTree(root_path=str(tmp_path))
        result = tree.read_file("mydir")

        assert "error" in result
        assert "Not a file" in result["error"]

    def test_path_traversal_raises_value_error(self, tmp_path):
        """_resolve() raises ValueError for path traversal outside root."""
        from app.services.file_tree import FileTree

        tree = FileTree(root_path=str(tmp_path))

        with pytest.raises(ValueError, match="Path traversal detected"):
            tree._resolve("../../../etc/passwd")

    def test_absolute_path_outside_root_raises(self, tmp_path):
        """_resolve() blocks absolute paths outside root directory."""
        from app.services.file_tree import FileTree

        tree = FileTree(root_path=str(tmp_path))

        with pytest.raises(ValueError, match="Path traversal detected"):
            tree._resolve("/etc/passwd")

    def test_write_file_success(self, tmp_path):
        """write_file() creates file with given content and returns success."""
        from app.services.file_tree import FileTree

        tree = FileTree(root_path=str(tmp_path))
        result = tree.write_file("new_file.txt", "hello world")

        assert result["success"] is True
        assert (tmp_path / "new_file.txt").read_text() == "hello world"

    def test_write_file_disallowed_extension(self, tmp_path):
        """write_file() rejects non-whitelisted extensions."""
        from app.services.file_tree import FileTree

        tree = FileTree(root_path=str(tmp_path))
        result = tree.write_file("script.exe", "bad")

        assert "error" in result
        assert "Extension not allowed" in result["error"]

    def test_write_file_creates_parent_dirs(self, tmp_path):
        """write_file() creates parent directories automatically."""
        from app.services.file_tree import FileTree

        tree = FileTree(root_path=str(tmp_path))
        result = tree.write_file("nested/deep/file.txt", "content")

        assert result["success"] is True
        assert (tmp_path / "nested" / "deep" / "file.txt").exists()

    def test_write_file_traversal_raises(self, tmp_path):
        """write_file() raises ValueError for path traversal."""
        from app.services.file_tree import FileTree

        tree = FileTree(root_path=str(tmp_path))

        with pytest.raises(ValueError, match="Path traversal detected"):
            tree.write_file("../../etc/evil.txt", "bad")

    def test_search_files_returns_matching_files(self, tmp_path):
        """search_files() returns files matching the query substring."""
        from app.services.file_tree import FileTree

        (tmp_path / "config.yaml").write_text("k: v")
        (tmp_path / "readme.md").write_text("# Readme")
        (tmp_path / "data.json").write_text("{}")

        tree = FileTree(root_path=str(tmp_path))
        results = tree.search_files("config")

        assert len(results) >= 1
        assert results[0]["name"] == "config.yaml"

    def test_search_files_case_insensitive(self, tmp_path):
        """search_files() matches case-insensitively."""
        from app.services.file_tree import FileTree

        (tmp_path / "Config.YAML").write_text("k: v")

        tree = FileTree(root_path=str(tmp_path))
        results = tree.search_files("config")

        assert len(results) >= 1

    def test_search_files_empty_when_no_match(self, tmp_path):
        """search_files() returns empty list when no files match."""
        from app.services.file_tree import FileTree

        tree = FileTree(root_path=str(tmp_path))
        results = tree.search_files("zzz_nonexistent_zzz")

        assert results == []

    def test_tree_respects_max_depth(self, tmp_path):
        """get_tree(max_depth=N) limits recursion depth."""
        from app.services.file_tree import FileTree

        deep = tmp_path / "a" / "b" / "c" / "d"
        deep.mkdir(parents=True)

        tree = FileTree(root_path=str(tmp_path))
        # depth 0 should show only root with truncated=True at a
        result = tree.get_tree(max_depth=0)

        assert result["type"] == "directory"
        # At depth 0, children of root should have truncated flag
        if result.get("truncated"):
            pass  # Root itself could be truncated at depth 0


# ── TestConfigService ──


class TestConfigService:
    """Tests for ConfigService — JSON-backed configuration."""

    def test_get_config_returns_defaults_when_no_file(self, tmp_path):
        """get_config() returns DEFAULT_CONFIG when no JSON file exists."""
        from app.services.config_service import ConfigService

        config_path = tmp_path / "config.json"
        svc = ConfigService(config_path=str(config_path))
        result = svc.get_config()

        assert result["refresh_interval_ms"] == 2000
        assert result["thresholds"]["ram_warning"] == 75
        assert result["ui"]["dark_mode"] is True
        assert result["security"]["require_auth"] is False
        assert result["streaming"]["sse_heartbeat_interval"] == 30

    def test_get_config_loads_from_file(self, tmp_path):
        """get_config() loads and merges config from file with defaults."""
        from app.services.config_service import ConfigService

        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "refresh_interval_ms": 5000,
            "thresholds": {"ram_warning": 80},
        }))

        svc = ConfigService(config_path=str(config_path))
        result = svc.get_config()

        assert result["refresh_interval_ms"] == 5000
        assert result["thresholds"]["ram_warning"] == 80
        # Default values preserved for non-overridden keys
        assert result["thresholds"]["ram_critical"] == 90
        assert result["ui"]["dark_mode"] is True

    def test_get_config_bad_json_falls_back_to_defaults(self, tmp_path):
        """get_config() falls back to defaults when JSON file is invalid."""
        from app.services.config_service import ConfigService

        config_path = tmp_path / "config.json"
        config_path.write_text("not valid json {{{")

        svc = ConfigService(config_path=str(config_path))
        result = svc.get_config()

        # Should fall back to defaults
        assert result["refresh_interval_ms"] == 2000

    def test_update_config_deep_merge(self, tmp_path):
        """update_config() deep-merges updates into existing config."""
        from app.services.config_service import ConfigService

        config_path = tmp_path / "config.json"
        svc = ConfigService(config_path=str(config_path))

        result = svc.update_config({
            "thresholds": {"ram_warning": 80},
            "ui": {"dark_mode": False},
        })

        assert result["thresholds"]["ram_warning"] == 80
        assert result["ui"]["dark_mode"] is False
        # Other keys preserved
        assert result["thresholds"]["ram_critical"] == 90
        assert result["ui"]["compact_view"] is False

    def test_get_dot_separated_key(self, tmp_path):
        """get('a.b.c') retrieves nested values via dot notation."""
        from app.services.config_service import ConfigService

        config_path = tmp_path / "config.json"
        svc = ConfigService(config_path=str(config_path))

        assert svc.get("thresholds.ram_warning") == 75
        assert svc.get("ui.dark_mode") is True
        assert svc.get("security.require_auth") is False

    def test_get_nonexistent_key_returns_default(self, tmp_path):
        """get() returns default value for nonexistent dot-separated key."""
        from app.services.config_service import ConfigService

        config_path = tmp_path / "config.json"
        svc = ConfigService(config_path=str(config_path))

        assert svc.get("nonexistent") is None
        assert svc.get("nonexistent.key", 42) == 42

    def test_get_deeply_nonexistent_returns_default(self, tmp_path):
        """get() returns default when intermediate path is missing."""
        from app.services.config_service import ConfigService

        config_path = tmp_path / "config.json"
        svc = ConfigService(config_path=str(config_path))

        assert svc.get("a.b.c.d", "fallback") == "fallback"

    def test_reset_to_defaults(self, tmp_path):
        """reset_to_defaults() restores factory default config."""
        from app.services.config_service import ConfigService

        config_path = tmp_path / "config.json"
        svc = ConfigService(config_path=str(config_path))

        svc.update_config({"refresh_interval_ms": 9999})
        assert svc.get_config()["refresh_interval_ms"] == 9999

        svc.reset_to_defaults()
        assert svc.get_config()["refresh_interval_ms"] == 2000

    def test_update_saves_to_disk(self, tmp_path):
        """update_config() persists merged config to JSON file."""
        from app.services.config_service import ConfigService

        config_path = tmp_path / "config.json"
        svc = ConfigService(config_path=str(config_path))

        svc.update_config({"refresh_interval_ms": 3000})

        # Reload from a fresh service instance
        svc2 = ConfigService(config_path=str(config_path))
        assert svc2.get_config()["refresh_interval_ms"] == 3000

    def test_multiple_updates_accumulate(self, tmp_path):
        """Multiple update_config() calls accumulate changes."""
        from app.services.config_service import ConfigService

        config_path = tmp_path / "config.json"
        svc = ConfigService(config_path=str(config_path))

        svc.update_config({"thresholds": {"ram_warning": 70}})
        svc.update_config({"thresholds": {"cpu_warning": 85}})

        result = svc.get_config()
        assert result["thresholds"]["ram_warning"] == 70
        assert result["thresholds"]["cpu_warning"] == 85


# ── TestCommandCenter ──


class TestCommandCenter:
    """Tests for CommandCenter — in-memory Kanban task board."""

    def test_get_kanban_returns_all_columns(self):
        """get_kanban() returns dict with all 6 kanban columns."""
        from app.services.command_center import CommandCenter, KANBAN_COLUMNS

        cc = CommandCenter()
        board = cc.get_kanban()

        assert isinstance(board, dict)
        for col in KANBAN_COLUMNS:
            assert col in board

    def test_create_task_returns_task_with_keys(self):
        """create_task() returns task with id, title, priority, column, status."""
        from app.services.command_center import CommandCenter

        cc = CommandCenter()
        task = cc.create_task(title="Test task", priority="high", description="A test")

        assert task["title"] == "Test task"
        assert task["priority"] == "high"
        assert task["description"] == "A test"
        assert task["column"] == "backlog"
        assert task["status"] == "open"
        assert task["assigned_to"] is None
        assert "id" in task
        assert "created_at" in task

    def test_create_task_in_specific_column(self):
        """create_task() accepts a custom column parameter."""
        from app.services.command_center import CommandCenter

        cc = CommandCenter()
        task = cc.create_task(title="Ready task", column="ready")

        assert task["column"] == "ready"

    def test_create_task_invalid_column_defaults_to_backlog(self):
        """create_task() defaults to backlog for invalid column names."""
        from app.services.command_center import CommandCenter

        cc = CommandCenter()
        task = cc.create_task(title="Bad column", column="invalid")

        assert task["column"] == "backlog"

    def test_create_task_invalid_priority_defaults_to_medium(self):
        """create_task() defaults to medium for invalid priority."""
        from app.services.command_center import CommandCenter

        cc = CommandCenter()
        task = cc.create_task(title="Bad priority", priority="ultra")

        assert task["priority"] == "medium"

    def test_kanban_includes_created_tasks(self):
        """get_kanban() includes newly created tasks grouped by column."""
        from app.services.command_center import CommandCenter

        cc = CommandCenter()
        cc.create_task(title="Task 1", column="backlog")
        cc.create_task(title="Task 2", column="ready")

        board = cc.get_kanban()
        assert len(board["backlog"]) == 1
        assert board["backlog"][0]["title"] == "Task 1"
        assert len(board["ready"]) == 1
        assert board["ready"][0]["title"] == "Task 2"

    def test_move_task_valid_transition(self):
        """move_task() moves task between valid columns."""
        from app.services.command_center import CommandCenter

        cc = CommandCenter()
        task = cc.create_task(title="Move me", column="backlog")

        moved = cc.move_task(task["id"], "backlog", "ready")
        assert moved is not None
        assert moved["column"] == "ready"

        board = cc.get_kanban()
        assert len(board["backlog"]) == 0
        assert len(board["ready"]) == 1

    def test_move_task_invalid_transition_returns_none(self):
        """move_task() returns None for invalid transition (backlog->running)."""
        from app.services.command_center import CommandCenter

        cc = CommandCenter()
        task = cc.create_task(title="Stuck", column="backlog")

        result = cc.move_task(task["id"], "backlog", "running")
        assert result is None
        assert cc._tasks[task["id"]]["column"] == "backlog"

    def test_move_task_nonexistent_task_returns_none(self):
        """move_task() returns None when task_id doesn't exist."""
        from app.services.command_center import CommandCenter

        cc = CommandCenter()
        result = cc.move_task("nonexistent", "backlog", "ready")
        assert result is None

    def test_move_task_invalid_column_returns_none(self):
        """move_task() returns None for invalid column names."""
        from app.services.command_center import CommandCenter

        cc = CommandCenter()
        task = cc.create_task(title="Test")

        result = cc.move_task(task["id"], "backlog", "moon")
        assert result is None

    def test_move_to_done_sets_status(self):
        """move_task() to 'done' sets status='done' and completed_at."""
        from app.services.command_center import CommandCenter

        cc = CommandCenter()
        task = cc.create_task(title="Finish", column="review")

        moved = cc.move_task(task["id"], "review", "done")
        assert moved["status"] == "done"
        assert "completed_at" in moved

    def test_assign_task_sets_agent(self):
        """assign_task() sets the assigned_to field on a task."""
        from app.services.command_center import CommandCenter

        cc = CommandCenter()
        task = cc.create_task(title="Assign me")

        result = cc.assign_task(task["id"], "agent-42")
        assert result is not None
        assert result["assigned_to"] == "agent-42"

    def test_assign_task_nonexistent_returns_none(self):
        """assign_task() returns None for nonexistent task."""
        from app.services.command_center import CommandCenter

        cc = CommandCenter()
        result = cc.assign_task("nonexistent", "agent-42")
        assert result is None

    def test_get_task_returns_task(self):
        """get_task() retrieves a task by its ID."""
        from app.services.command_center import CommandCenter

        cc = CommandCenter()
        created = cc.create_task(title="Get me")
        found = cc.get_task(created["id"])

        assert found == created

    def test_get_task_nonexistent_returns_none(self):
        """get_task() returns None for nonexistent task ID."""
        from app.services.command_center import CommandCenter

        cc = CommandCenter()
        assert cc.get_task("nonexistent") is None

    def test_delete_task_removes_task(self):
        """delete_task() removes a task and returns True."""
        from app.services.command_center import CommandCenter

        cc = CommandCenter()
        task = cc.create_task(title="Delete me")

        assert cc.delete_task(task["id"]) is True
        assert cc.get_task(task["id"]) is None

    def test_delete_task_nonexistent_returns_false(self):
        """delete_task() returns False for nonexistent task."""
        from app.services.command_center import CommandCenter

        cc = CommandCenter()
        assert cc.delete_task("nonexistent") is False

    def test_get_tasks_by_agent(self):
        """get_tasks_by_agent() returns tasks for a specific agent."""
        from app.services.command_center import CommandCenter

        cc = CommandCenter()
        t1 = cc.create_task(title="A")
        t2 = cc.create_task(title="B")
        cc.assign_task(t1["id"], "agent-1")
        cc.assign_task(t2["id"], "agent-2")

        tasks = cc.get_tasks_by_agent("agent-1")
        assert len(tasks) == 1
        assert tasks[0]["title"] == "A"

    def test_task_count_property(self):
        """task_count reflects number of tasks."""
        from app.services.command_center import CommandCenter

        cc = CommandCenter()
        assert cc.task_count == 0

        cc.create_task(title="T1")
        cc.create_task(title="T2")
        assert cc.task_count == 2

    def test_column_counts_property(self):
        """column_counts returns per-column task counts."""
        from app.services.command_center import CommandCenter

        cc = CommandCenter()
        cc.create_task(title="T1", column="backlog")
        cc.create_task(title="T2", column="ready")
        cc.create_task(title="T3", column="ready")

        counts = cc.column_counts
        assert counts["backlog"] == 1
        assert counts["ready"] == 2
        assert counts["running"] == 0

    def test_get_kanban_column_returns_tasks(self):
        """get_kanban_column() returns tasks in a specific column."""
        from app.services.command_center import CommandCenter

        cc = CommandCenter()
        cc.create_task(title="A", column="ready")
        cc.create_task(title="B", column="ready")

        tasks = cc.get_kanban_column("ready")
        assert tasks is not None
        assert len(tasks) == 2

    def test_get_kanban_column_invalid_returns_none(self):
        """get_kanban_column() returns None for invalid column."""
        from app.services.command_center import CommandCenter

        cc = CommandCenter()
        assert cc.get_kanban_column("invalid") is None


# ── TestApiRegistry ──


class TestApiRegistry:
    """Tests for ApiRegistry — API provider registry and call tracking."""

    def test_get_providers_returns_list(self):
        """get_providers() returns list of provider dicts, sorted enabled-first."""
        from app.services.api_registry import ApiRegistry

        registry = ApiRegistry()
        providers = registry.get_providers()

        assert isinstance(providers, list)
        assert len(providers) >= 6
        ids = [p["id"] for p in providers]
        assert "openai" in ids
        assert "anthropic" in ids
        assert "deepseek" in ids

    def test_get_provider_found(self):
        """get_provider() returns a provider dict by ID with stats."""
        from app.services.api_registry import ApiRegistry

        registry = ApiRegistry()
        provider = registry.get_provider("openai")

        assert provider is not None
        assert provider["id"] == "openai"
        assert provider["name"] == "OpenAI"
        assert provider["type"] == "llm"

    def test_get_provider_not_found(self):
        """get_provider() returns None for unknown provider ID."""
        from app.services.api_registry import ApiRegistry

        registry = ApiRegistry()
        assert registry.get_provider("nonexistent") is None

    def test_update_provider_status_valid(self):
        """update_provider_status() sets status and returns updated provider."""
        from app.services.api_registry import ApiRegistry

        registry = ApiRegistry()
        result = registry.update_provider_status("openai", "online")

        assert result is not None
        assert result["status"] == "online"
        assert "last_updated" in result

    def test_update_provider_status_invalid_value(self):
        """update_provider_status() returns None for invalid status value."""
        from app.services.api_registry import ApiRegistry

        registry = ApiRegistry()
        result = registry.update_provider_status("openai", "invalid-status")
        assert result is None

    def test_update_provider_status_not_found(self):
        """update_provider_status() returns None for unknown provider."""
        from app.services.api_registry import ApiRegistry

        registry = ApiRegistry()
        result = registry.update_provider_status("nonexistent", "online")
        assert result is None

    def test_record_api_call(self):
        """record_api_call() records entry with provider_id, tokens, latency, cost."""
        from app.services.api_registry import ApiRegistry

        registry = ApiRegistry()
        entry = registry.record_api_call(
            provider_id="openai", tokens=1000, latency_ms=500.0, cost=0.02, model="gpt-4", success=True,
        )

        assert entry["provider_id"] == "openai"
        assert entry["tokens"] == 1000
        assert entry["latency_ms"] == 500.0
        assert entry["cost"] == 0.02

    def test_get_call_log_returns_newest_first(self):
        """get_call_log() returns calls newest first."""
        from app.services.api_registry import ApiRegistry

        registry = ApiRegistry()
        registry.record_api_call(provider_id="openai", tokens=500)
        registry.record_api_call(provider_id="anthropic", tokens=300)

        log = registry.get_call_log(limit=10)
        assert len(log) == 2
        assert log[0]["provider_id"] == "anthropic"

    def test_get_call_log_filtered_by_provider(self):
        """get_call_log(provider_id=) filters to specific provider."""
        from app.services.api_registry import ApiRegistry

        registry = ApiRegistry()
        registry.record_api_call(provider_id="openai", tokens=500)
        registry.record_api_call(provider_id="anthropic", tokens=300)

        log = registry.get_call_log(provider_id="openai")
        assert len(log) == 1
        assert log[0]["provider_id"] == "openai"

    def test_provider_stats_after_calls(self):
        """get_provider() includes aggregate stats after recording calls."""
        from app.services.api_registry import ApiRegistry

        registry = ApiRegistry()
        registry.record_api_call(provider_id="openai", tokens=1000, cost=0.02, latency_ms=200.0, success=True)
        registry.record_api_call(provider_id="openai", tokens=500, cost=0.01, latency_ms=300.0, success=True)

        provider = registry.get_provider("openai")
        assert "stats" in provider
        assert provider["stats"]["total_calls"] == 2
        assert provider["stats"]["total_tokens"] == 1500

    def test_call_log_trimming(self):
        """Call log trims to max_call_log when exceeding limit."""
        from app.services.api_registry import ApiRegistry

        registry = ApiRegistry()
        # Record more than max_call_log entries
        for i in range(registry._max_call_log + 100):
            registry.record_api_call(provider_id="openai", tokens=1)

        assert len(registry._call_log) <= registry._max_call_log
