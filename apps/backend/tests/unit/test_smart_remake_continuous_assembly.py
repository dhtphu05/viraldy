from __future__ import annotations

import copy

import pytest

from viraldy.modules.smart_remake import timeline_media


def item(start: int, end: int):
    return {"inFrame": start, "outFrame": end, "targetDurationFrames": end - start}


def test_adjacent_source_ranges_are_rendered_as_two_complete_provider_clips(monkeypatch):
    inputs = [b"first"] * 3 + [b"second"] * 3
    items = [item(start, end) for start, end in [(0, 24), (24, 80), (80, 144)] * 2]
    original = copy.deepcopy(items)
    commands = []

    def run(argv, **_):
        from pathlib import Path

        commands.append(argv)
        Path(argv[-1]).write_bytes(b"encoded")

    monkeypatch.setattr(timeline_media.subprocess, "run", run)
    monkeypatch.setattr(timeline_media, "probe_timeline_media", lambda _: {"hasAudio": True})
    assert timeline_media._assemble(inputs, items, resolution="480P") == b"encoded"
    filters = [command[command.index("-filter_complex") + 1]
               for command in commands if "-filter_complex" in command]
    assert len(filters) == 2
    assert all("trim=start_frame=0:end_frame=144" in value for value in filters)
    assert items == original


@pytest.mark.parametrize("second, ranges", [
    (b"different", [(0, 48), (48, 96)]),
    (b"same", [(0, 48), (49, 97)]),
    (b"same", [(0, 48), (24, 72)]),
    (b"same", [(0, 48), (0, 48)]),
])
def test_different_clips_gaps_overlaps_and_repeated_ranges_remain_separate(
    monkeypatch, second, ranges,
):
    commands = []

    def run(argv, **_):
        from pathlib import Path

        commands.append(argv)
        Path(argv[-1]).write_bytes(b"encoded")

    monkeypatch.setattr(timeline_media.subprocess, "run", run)
    monkeypatch.setattr(timeline_media, "probe_timeline_media", lambda _: {"hasAudio": True})
    timeline_media._assemble([b"same", second], [item(*bounds) for bounds in ranges])
    assert sum("-filter_complex" in command for command in commands) == 2
