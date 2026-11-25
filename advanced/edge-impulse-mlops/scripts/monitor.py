"""Vérifie la Nano KWS, enregistre des fenêtres et calcule un rapport local."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import wave
import zlib
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import numpy as np
import serial

from tinyml2027.capture import CaptureError, open_port, pick_port

LABELS = ("bruit", "go", "stop")
OUTCOMES = (*LABELS, "uncertain")
MAX_LINE = 2048
PCM_BYTES = 32000
REPLAY_CHUNK = 128
USB_WRITE_SIZE = 32


class MonitorError(RuntimeError):
    pass


def natural(value):
    return type(value) is int and value >= 0


def parse_message(raw):
    try:
        value = json.loads(raw)
    except (UnicodeError, ValueError):
        raise MonitorError("Trame JSONL illisible.") from None
    if not isinstance(value, dict):
        raise MonitorError("Objet JSON attendu.")
    kind = value.get("event")
    if kind == "hello":
        if (value.get("protocol") != 2 or value.get("sample_rate_hz") != 16000 or value.get("samples") != 16000
                or value.get("threshold") != 0.6 or not isinstance(value.get("firmware"), str)
                or not re.fullmatch(r"kws-v[1-9][0-9]*", str(value.get("release")))
                or not re.fullmatch(r"[a-f0-9]{64}", str(value.get("export_sha256")))
                or type(value.get("mic_ok")) is not bool or type(value.get("model_ok")) is not bool):
            raise MonitorError("Annonce de firmware invalide.")
    elif kind not in ("capture_started", "replay_ready", "replay_chunk", "prediction", "error") or not natural(value.get("seq")):
        raise MonitorError("Type ou numéro de trame inattendu.")
    elif kind == "replay_ready" and (value.get("bytes") != PCM_BYTES or value.get("chunk_bytes") != REPLAY_CHUNK):
        raise MonitorError("Le nombre d’octets attendu par le firmware diffère.")
    elif kind == "error" and (not isinstance(value.get("code"), str) or not natural(value.get("pdm_errors"))):
        raise MonitorError("Trame d’erreur incomplète.")
    elif kind == "prediction":
        for field in ("capture_us", "inference_us", "dsp_ms", "classification_ms",
                      "discarded_during_inference", "pdm_errors", "pcm_crc32"):
            if not natural(value.get(field)):
                raise MonitorError(f"Champ {field} invalide.")
        scores = value.get("scores")
        rms = value.get("rms_pcm")
        if (not isinstance(scores, dict) or set(scores) != set(LABELS)
                or any(type(x) not in (int, float) or not 0 <= x <= 1 for x in scores.values())
                or type(rms) not in (int, float) or not 0 <= rms <= 32768 or value["pcm_crc32"] > 0xffffffff
                or value.get("mode") not in ("microphone", "replay")):
            raise MonitorError("Valeur de prédiction invalide.")
        best = max(LABELS, key=scores.__getitem__)
        if value.get("prediction") != (best if scores[best] >= 0.6 else "uncertain"):
            raise MonitorError("La classe et le seuil annoncés sont incohérents.")
    return value


def read_message(port, timeout=8):
    deadline = time.monotonic() + timeout
    frame = bytearray()
    while time.monotonic() < deadline:
        frame.extend(port.read_until(b"\n", MAX_LINE + 1 - len(frame)))
        if len(frame) > MAX_LINE:
            raise MonitorError("Trame série trop longue.")
        if frame.endswith(b"\n"):
            return parse_message(bytes(frame))
    raise MonitorError("Aucune trame complète reçue dans le délai.")


def expect(port, kind, seq=None):
    value = read_message(port)
    if value["event"] == "error":
        if seq is not None and value["seq"] != seq:
            raise MonitorError("Numéro de trame d’erreur inattendu.")
        return value
    if value["event"] != kind or (seq is not None and value.get("seq") != seq):
        raise MonitorError(f"Trame {kind} attendue.")
    return value


def handshake(port, expected_sha=None):
    port.write(b"I")
    value = expect(port, "hello")
    if value["event"] != "hello" or value.get("board") != "ABX00031" or not value["model_ok"] or not value["mic_ok"]:
        raise MonitorError(f"Carte, modèle ou microphone non prêt : {value}")
    if expected_sha and value["export_sha256"] != expected_sha:
        raise MonitorError("Empreinte annoncée différente de celle du ZIP attendu.")
    return value


def read_pcm(path):
    with wave.open(str(path), "rb") as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()) != (1, 2, 16000, 16000):
            raise MonitorError(f"{path.name} : WAV mono PCM16, 16 kHz et 1 s requis.")
        pcm = wav.readframes(16000)
    if len(pcm) != PCM_BYTES:
        raise MonitorError(f"{path.name} : fenêtre PCM incomplète.")
    return pcm


def studio_reference(path):
    if path is None:
        return {}
    body = json.loads(path.read_text(encoding="utf-8"))
    if body.get("success") is not True:
        raise MonitorError("Réponse Studio invalide.")
    accepted = {row["sampleId"]: row["prediction"] for row in body["predictions"]}
    return {
        row["sample"]["filename"]: (row["classifications"][0]["result"][0], accepted[row["sampleId"]])
        for row in body["result"]
    }


def replay(port, clip, reference):
    pcm = read_pcm(clip)
    port.write(b"R")
    ready = expect(port, "replay_ready")
    if ready["event"] == "error":
        return ready
    for start in range(0, PCM_BYTES, REPLAY_CHUNK):
        end = start + REPLAY_CHUNK
        # Une écriture USB pleine peut rester tamponnée par le pilote CDC du poste.
        for offset in range(start, end, USB_WRITE_SIZE):
            port.write(pcm[offset:offset + USB_WRITE_SIZE])
            port.flush()
            time.sleep(0.003)
        if end != PCM_BYTES:
            ack = expect(port, "replay_chunk", ready["seq"])
            if ack["event"] == "error":
                return ack
            if ack.get("received") != end:
                raise MonitorError("Le firmware a reçu une longueur de bloc inattendue.")
    result = expect(port, "prediction", ready["seq"])
    if result["event"] == "error":
        return result
    if result["mode"] != "replay" or result["pcm_crc32"] != zlib.crc32(pcm):
        raise MonitorError("CRC32 ou mode du rejeu différent des données envoyées.")
    if clip.stem in reference:
        expected, label = reference[clip.stem]
        delta = max(abs(result["scores"][name] - expected[name]) for name in LABELS)
        result["studio_scores"] = expected
        result["studio_prediction"] = label
        result["max_score_delta"] = delta
        result["matches_studio"] = delta <= 1 / 256 + 0.00001 and result["prediction"] == label
    return result


def capture(port, clip=None, volume=0.5):
    port.write(b"C")
    started = expect(port, "capture_started")
    if started["event"] == "error":
        return started
    if clip is None:
        result = expect(port, "prediction", started["seq"])
    else:
        with subprocess.Popen(["afplay", "-v", str(volume), str(clip)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as playback:
            result = expect(port, "prediction", started["seq"])
            if playback.wait(timeout=5) != 0:
                raise MonitorError("Échec de lecture audio sur le Mac.")
    if result["event"] == "prediction" and result["mode"] != "microphone":
        raise MonitorError("Prédiction microphone attendue.")
    return result


def record(args, port):
    hello = handshake(port, args.expect_sha256)
    print(json.dumps(hello, ensure_ascii=False), flush=True)
    if args.command == "check":
        return 0
    clips = args.clips if args.command in ("replay", "play") else [None] * args.count
    for clip in clips:
        if clip is not None:
            read_pcm(clip)
            if clip.name.split(".", 1)[0] not in LABELS:
                raise MonitorError(f"Étiquette absente du nom {clip.name}.")
    reference = studio_reference(args.studio_json) if args.command == "replay" else {}
    if args.command == "replay" and args.studio_json and any(clip.stem not in reference for clip in clips):
        raise MonitorError("Certaines fenêtres n’ont aucune prédiction Studio dans le fichier fourni.")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    bad = False
    with args.out.open("x", encoding="utf-8", newline="\n") as stream:
        def append(event):
            event["host_time_utc"] = datetime.now(timezone.utc).isoformat()
            stream.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
            stream.flush()

        append(hello | {"session_note": args.note, "protocol_mode": args.command})
        for clip in clips:
            label = clip.name.split(".", 1)[0] if clip else args.label
            if args.command == "capture" and args.prompt:
                input(f"Entrée pour armer la capture {label or 'non étiquetée'}… ")
                for count in (3, 2, 1):
                    print(count, flush=True)
                    time.sleep(1)
                print("Restez silencieux." if label == "bruit" else "Prononcez la commande maintenant.", flush=True)
            try:
                event = replay(port, clip, reference) if args.command == "replay" else capture(
                    port, clip, getattr(args, "volume", 0.5),
                )
            except (MonitorError, serial.SerialException, OSError, subprocess.SubprocessError) as error:
                append({"event": "host_error", "label": label, "clip": clip.name if clip else None,
                        "detail": str(error)})
                raise
            append(event | {"label": label, "clip": clip.name if clip else None})
            print(json.dumps(event, ensure_ascii=False), flush=True)
            bad |= event["event"] == "error" or event.get("matches_studio") is False
    return int(bad)


def counts(values):
    return dict(Counter(values))


def summarize(entries):
    predictions = [r for r in entries if r["event"] == "prediction"]
    elapsed = [r["inference_us"] / 1000 for r in predictions]
    durations = [r["capture_us"] / 1000 for r in predictions if r["mode"] == "microphone"]
    labeled = [r for r in predictions if r.get("label") in LABELS]
    noise = [r for r in labeled if r["label"] == "bruit"]
    commands = [r for r in labeled if r["label"] in ("go", "stop")]
    unit = [r for r in predictions if "matches_studio" in r]
    sequences = [r["seq"] for r in entries if r["event"] in ("prediction", "error")]
    observed_totals = [(r["capture_us"] + r["inference_us"]) / 1000
                       for r in predictions if r["mode"] == "microphone"]
    return {
        "windows": len(predictions), "predicted": counts(r["prediction"] for r in predictions),
        "best_score_distribution": [
            {"range": f"[{a / 10:.1f}, {(a + 1) / 10:.1f}{']' if a == 9 else ')'}",
             "n": sum(min(9, int(10 * max(r["scores"].values()))) == a for r in predictions)}
            for a in range(10)
        ],
        "uncertain": sum(r["prediction"] == "uncertain" for r in predictions),
        "inference_mean_ms": float(np.mean(elapsed)) if elapsed else None,
        "inference_p95_ms": float(np.percentile(elapsed, 95)) if elapsed else None,
        "capture_mean_ms": float(np.mean(durations)) if durations else None,
        "capture_plus_inference_p95_ms": float(np.percentile(observed_totals, 95)) if observed_totals else None,
        "discarded_during_inference": sum(r["discarded_during_inference"] for r in predictions),
        "errors": counts(r.get("code", "host_error") for r in entries if r["event"] in ("error", "host_error")),
        "pdm_errors_max": max((r.get("pdm_errors", 0) for r in entries), default=0),
        "missing_sequence_ids": sum(max(0, b-a-1) for a,b in zip(sequences, sequences[1:])),
        "command_trials": len(commands), "misses": sum(r["prediction"] != r["label"] for r in commands),
        "noise_trials": len(noise), "false_triggers": sum(r["prediction"] in ("go", "stop") for r in noise),
        "replay_comparisons": len(unit), "replay_matches": sum(r["matches_studio"] for r in unit),
        "replay_max_score_delta": max((r["max_score_delta"] for r in unit), default=None),
    }


def write_html(path, entries, summary):
    def table(headers, rows):
        head = "".join(f"<th>{escape(str(item))}</th>" for item in headers)
        body = "".join("<tr>" + "".join(f"<td>{escape(str(item))}</td>" for item in row) + "</tr>"
                       for row in rows)
        return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

    runs = [r for r in entries if r["event"] == "prediction"]
    hello = next((r for r in entries if r["event"] == "hello"), {})
    metrics = [(name, f"{value:.3f}" if isinstance(value, float) else value)
               for name, value in summary.items() if name != "best_score_distribution"]
    windows = [(r["seq"], r["mode"], r.get("label") or "—", r["prediction"],
                *(f'{r["scores"][label]:.3f}' for label in LABELS), r["dsp_ms"], r["classification_ms"])
               for r in runs]
    score_hist = [(row["range"], row["n"]) for row in summary["best_score_distribution"]]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as output:
        output.write("<!doctype html><html lang=fr><meta charset=utf-8><title>Monitoring KWS</title>"
                     "<style>body{font:16px system-ui;margin:2rem auto;padding:0 1rem;color:#183240;max-width:1100px}"
                     "table{border-collapse:collapse;margin-bottom:1.4rem}th,td{padding:.45rem .7rem;"
                     "border-bottom:1px solid #bcd1dc;text-align:left}th{background:#e5f0f5}</style>"
                     "<main><h1>Monitoring de la Nano</h1>")
        output.write(f"<p>{escape(str(hello.get('release', '')))} · {escape(str(hello.get('protocol_mode', '')))}</p>")
        output.write(f"<p>{escape(str(hello.get('session_note', '')))}</p>")
        if summary["inference_p95_ms"] is not None:
            output.write(f"<p><strong>{summary['windows']} fenêtres</strong> · "
                         f"p95 de l’inférence {summary['inference_p95_ms']:.2f} ms · "
                         f"{summary['uncertain']} réponses incertaines</p>")
        if summary["replay_comparisons"]:
            output.write(f"<p><strong>Parité Studio {summary['replay_matches']}/"
                         f"{summary['replay_comparisons']}</strong> · "
                         f"écart max {summary['replay_max_score_delta']:.2g}</p>")
        output.write("<h2>Mesures</h2>" + table(("Indicateur", "Valeur"), metrics))
        output.write("<h2>Distribution du meilleur score</h2>" + table(("Intervalle", "Fenêtres"), score_hist))
        output.write("<h2>Prédictions</h2>" + table(
            ("N°", "Mode", "Étiquette", "Prédiction", "bruit", "go", "stop", "DSP (ms)", "Classification (ms)"),
            windows,
        ))
        output.write("</main></html>")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port")
    parser.add_argument("--expect-sha256")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check")
    for mode in ("capture", "replay", "play"):
        command = commands.add_parser(mode)
        command.add_argument("--out", required=True, type=Path)
        command.add_argument("--note", default="")
        if mode != "capture":
            command.add_argument("clips", type=Path, nargs="+")
        if mode == "capture":
            command.add_argument("--count", type=int, default=1)
            command.add_argument("--label", choices=LABELS)
            command.add_argument("--prompt", action="store_true")
        if mode == "replay":
            command.add_argument("--studio-json", type=Path)
        if mode == "play":
            command.add_argument("--volume", type=float, default=0.5)
    report = commands.add_parser("report")
    report.add_argument("path", type=Path)
    report.add_argument("--html", type=Path, help="écrire également un rapport HTML local")
    args = parser.parse_args()
    try:
        if args.command == "report":
            with args.path.open(encoding="utf-8") as stream:
                entries = [json.loads(line) for line in stream]
            summary = summarize(entries)
            if args.html:
                write_html(args.html, entries, summary)
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0
        if args.command == "capture" and args.count < 1:
            raise MonitorError("Le nombre de fenêtres doit être positif.")
        if args.command == "play" and not 0 < args.volume <= 1:
            raise MonitorError("Le gain de lecture doit être dans ]0, 1].")
        device, _ = pick_port(args.port)
        with open_port(device) as port:
            port.write_timeout = 5
            return record(args, port)
    except (CaptureError, MonitorError, OSError, ValueError, KeyError, wave.Error, subprocess.SubprocessError) as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Mesure interrompue. Les trames déjà écrites sont conservées.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
