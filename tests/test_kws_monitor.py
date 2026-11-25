import importlib.util
import json
import zlib
from pathlib import Path
from wave import open as open_wave

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "advanced/edge-impulse-mlops/scripts/monitor.py"
spec = importlib.util.spec_from_file_location("kws_monitor", SCRIPT)
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


def prediction(**fields):
    return {
        "event": "prediction", "seq": 1, "mode": "microphone", "capture_us": 1000000,
        "inference_us": 140000, "dsp_ms": 134, "classification_ms": 6, "discarded_during_inference": 2048,
        "pdm_errors": 0, "pcm_crc32": 0, "rms_pcm": 10.5,
        "scores": {"bruit": 0.65, "go": 0.2, "stop": 0.15}, "prediction": "bruit",
        **fields,
    }


class Port:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.sent = []

    def write(self, data):
        self.sent.append(data)

    def flush(self):
        pass

    def read_until(self, *_):
        return next(self.responses)


def frame(data):
    return json.dumps(data).encode() + b"\n"


def test_fragmented_json_and_bad_scores():
    sample = frame(prediction())
    assert monitor.read_message(Port(sample[:7], sample[7:]))["prediction"] == "bruit"
    with pytest.raises(monitor.MonitorError, match="seuil"):
        monitor.parse_message(frame(prediction(prediction="uncertain")))
    with pytest.raises(monitor.MonitorError, match="illisible"):
        monitor.parse_message(b"{")
    with pytest.raises(monitor.MonitorError, match="trop longue"):
        monitor.read_message(Port(b"x" * (monitor.MAX_LINE + 1)))


def test_replay_verifies_checksum_and_score(tmp_path, monkeypatch):
    monkeypatch.setattr(monitor.time, "sleep", lambda _: None)
    clip = tmp_path / "bruit.promotion.wav"
    pcm = bytes(monitor.PCM_BYTES)
    with open_wave(str(clip), "wb") as out:
        out.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        out.writeframes(pcm)
    ready = {"event": "replay_ready", "seq": 1, "bytes": monitor.PCM_BYTES, "chunk_bytes": monitor.REPLAY_CHUNK}
    acknowledgments = [
        frame({"event": "replay_chunk", "seq": 1, "received": offset})
        for offset in range(monitor.REPLAY_CHUNK, monitor.PCM_BYTES, monitor.REPLAY_CHUNK)
    ]
    response = prediction(mode="replay", capture_us=0, pcm_crc32=zlib.crc32(pcm))
    port = Port(frame(ready), *acknowledgments, frame(response))
    assert monitor.replay(port, clip, {clip.stem: (response["scores"], "bruit")})["matches_studio"]
    assert port.sent[0] == b"R" and b"".join(port.sent[1:]) == pcm
    assert all(len(chunk) == monitor.USB_WRITE_SIZE for chunk in port.sent[1:])
    with pytest.raises(monitor.MonitorError, match="CRC32"):
        monitor.replay(Port(frame(ready), *acknowledgments, frame(dict(response, pcm_crc32=1))), clip, {})


def test_monitor_counts_labeled_errors_and_replay(tmp_path):
    runs = [prediction(label="go"),
            prediction(seq=3, label="bruit", prediction="go", scores={"bruit": .1, "go": .8, "stop": .1}),
            prediction(seq=4, mode="replay", matches_studio=True, max_score_delta=0.001),
            {"event": "error", "seq": 5, "code": "capture_timeout"}]
    report = monitor.summarize(runs)
    assert report["misses"] == report["false_triggers"] == report["missing_sequence_ids"] == 1
    assert report["inference_p95_ms"] == 140
    assert report["capture_plus_inference_p95_ms"] == 1140
    assert report["replay_matches"] == 1
    assert report["errors"] == {"capture_timeout": 1}
    output = tmp_path / "rapport.html"
    monitor.write_html(output, [{"event": "hello", "session_note": "<note>"}] + runs, report)
    assert "&lt;note&gt;" in output.read_text(encoding="utf-8")
