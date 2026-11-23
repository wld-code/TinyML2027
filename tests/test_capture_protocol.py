"""Protocole série du firmware imu_capture, testé avec une carte simulée (sans matériel).

Ces tests prouvent que l'outil Python réagit correctement aux réponses du protocole :
ils ne prouvent rien sur la carte réelle.
"""

import types

import pytest

from tinyml2027 import capture, dataset, recording


class FakeBoard:
    """Imite imu_capture : INFO / START <id> / STOP, ~114 Hz, défauts injectables."""

    def __init__(self, drop_every=0, lose_end=False, error_on_start=None):
        self.out: list[bytes] = []
        self.recording = False
        self.seq = 0
        self.t = 0
        self.drop_every = drop_every
        self.lose_end = lose_end
        self.error_on_start = error_on_start

    def write(self, data: bytes):
        for cmd in data.decode().splitlines():
            if cmd == "INFO":
                self.out.append(b"INFO firmware=fake board_revision=original imu=LSM9DS1 odr_nominal_hz=119.00\r\n")
            elif cmd.startswith("START "):
                if self.error_on_start:
                    self.out.append(f"ERREUR {self.error_on_start}\r\n".encode())
                    continue
                self.recording, self.seq, self.t = True, 0, 0
                self.out.append(f"BEGIN recording_id={cmd[6:]} firmware=fake board_revision=original imu=LSM9DS1 "
                                "odr_nominal_hz=119.00\r\n".encode())
                self.out.append(b"seq,t_us,ax_g,ay_g,az_g\r\n")
            elif cmd == "STOP":
                self.recording = False
                if not self.lose_end:
                    self.out.append(f"END recording_id=x n={self.seq}\r\n".encode())
        return len(data)

    def readline(self):
        if self.recording and not self.out:
            line = f"{self.seq},{self.t},0.00100,-0.01000,0.96000\r\n".encode()
            self.seq += 1
            self.t += 8760
            if self.drop_every and self.seq % self.drop_every == 0:
                return self.readline()          # ligne perdue côté USB : la carte l'a comptée
            return line
        return self.out.pop(0) if self.out else b""

    def reset_input_buffer(self):
        self.out.clear()


@pytest.fixture
def fast_clock(monkeypatch):
    """Horloge simulée : chaque lecture avance le temps d'un échantillon."""
    now = [0.0]

    def monotonic():
        now[0] += 1 / 114
        return now[0]

    monkeypatch.setattr(capture.time, "monotonic", monotonic)
    monkeypatch.setattr(capture.time, "sleep", lambda s: None)


def args_for(tmp_path, **kw):
    base = dict(session="s01", duration=5.0, countdown=0, min_windows=1, data=str(tmp_path), yes=True)
    base.update(kw)
    return types.SimpleNamespace(**base)


def test_info_command_parses_fields():
    b = FakeBoard()
    line = capture.command(b, "INFO", "INFO")
    assert capture.parse_fields(line)["imu"] == "LSM9DS1"


def test_clean_capture_is_accepted_and_traced(tmp_path, fast_clock):
    ok = capture.record_one(FakeBoard(), "SN123", args_for(tmp_path), "stationary", 1)
    assert ok
    rows = dataset.read_manifest(tmp_path)
    assert rows[0]["recording_id"] == "s01_stationary_t01" and rows[0]["valid"] == "1"
    assert rows[0]["board_id"] != "SN123"           # numéro de série non stocké en clair
    df = recording.read_csv(tmp_path / "raw/s01/s01_stationary_t01.csv")
    assert len(df) > 256


def test_lost_lines_are_detected_and_rejected(tmp_path, fast_clock):
    ok = capture.record_one(FakeBoard(drop_every=50), None, args_for(tmp_path), "periodic", 1)
    assert not ok
    row = dataset.read_manifest(tmp_path)[0]
    assert row["valid"] == "0" and "reçus" in row["notes"]
    assert (tmp_path / "rejected/s01/s01_periodic_t01.csv").exists()


def test_missing_end_means_disconnection(tmp_path, fast_clock):
    with pytest.raises(capture.CaptureError, match="END"):
        capture.record_one(FakeBoard(lose_end=True), None, args_for(tmp_path), "impact", 1)


def test_firmware_error_is_reported(tmp_path, fast_clock):
    with pytest.raises(capture.CaptureError, match="imu_begin"):
        capture.record_one(FakeBoard(error_on_start="imu_begin"), None, args_for(tmp_path), "impact", 1)


def test_duplicate_recording_id_refused(tmp_path, fast_clock):
    capture.record_one(FakeBoard(), None, args_for(tmp_path), "stationary", 1)
    with pytest.raises(capture.CaptureError, match="existe déjà"):
        capture.record_one(FakeBoard(), None, args_for(tmp_path), "stationary", 1)


def test_no_response_from_wrong_firmware():
    class Silent(FakeBoard):
        def write(self, data):
            return len(data)
    with pytest.raises(capture.CaptureError, match="imu_capture"):
        capture.command(Silent(), "INFO", "INFO", timeout_s=0.01)


def test_pick_port_refuses_ambiguity(monkeypatch):
    P = types.SimpleNamespace
    ports = [P(device="/dev/a", description="Nano", vid=0x2341, pid=1, serial_number="1"),
             P(device="/dev/b", description="Nano", vid=0x2341, pid=1, serial_number="2")]
    monkeypatch.setattr(capture, "list_ports", lambda: ports)
    with pytest.raises(capture.CaptureError, match="2 carte"):
        capture.pick_port(None)
    monkeypatch.setattr(capture, "list_ports", lambda: ports[:1])
    assert capture.pick_port(None) == ("/dev/a", "1")
