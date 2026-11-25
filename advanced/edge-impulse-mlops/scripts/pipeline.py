"""Pilote un projet Edge Impulse privé et évalue un candidat KWS."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
import zipfile
from copy import deepcopy
from io import BytesIO
from pathlib import Path

import requests

from score_studio import LABELS, SPLITS

STUDIO = "https://studio.edgeimpulse.com/v1"
INGESTION = "https://ingestion.edgeimpulse.com"
UPLOAD_SPLITS = {
    "train-v1": "training", "corrective-v2": "training",
    "evaluation-clean": "testing", "evaluation-shifted": "testing",
}
LAB = Path(__file__).resolve().parents[1]
DEFAULT_DATA = Path("data/edge-impulse-mlops/datasets")


class PipelineError(RuntimeError):
    pass


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def file_sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def manifest_rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


class EdgeImpulse:
    def __init__(self, project_id, project_name, key, session=None):
        if not key:
            raise PipelineError("Définissez EI_API_KEY dans l’environnement du processus.")
        self.project_id = project_id
        self.project_name = project_name
        self.headers = {"x-api-key": key}
        self.session = session if session is not None else requests.Session()

    def request(self, method, url, *, headers=None, binary=False, **kwargs):
        # Une écriture interrompue peut avoir réussi sur le serveur.
        attempts = 3 if method == "GET" else 1
        for attempt in range(attempts):
            try:
                response = self.session.request(
                    method, url, headers={**self.headers, **(headers or {})},
                    timeout=(5, 30), allow_redirects=False, **kwargs,
                )
            except requests.RequestException:
                if attempt + 1 == attempts:
                    hint = " Vérifiez l’inventaire ou les jobs avant de réessayer." if method == "POST" else ""
                    raise PipelineError(f"{method} interrompu par une erreur réseau.{hint}") from None
                time.sleep(2 ** attempt)
                continue
            status = response.status_code
            if (status == 429 or status >= 500) and attempt + 1 < attempts:
                try:
                    delay = float(response.headers.get("Retry-After", 2 ** attempt))
                except ValueError:
                    delay = 2 ** attempt
                if 0 <= delay <= 30:
                    time.sleep(delay)
                    continue
            if not 200 <= status < 300:
                hint = " Vérifiez les droits ou le quota." if status in (401, 403, 429) else ""
                if method == "POST" and status >= 500:
                    hint += " Vérifiez l’état distant avant de renvoyer la requête."
                raise PipelineError(f"{method} refusé par Edge Impulse (HTTP {status}).{hint}")
            if binary:
                return response.content
            try:
                body = response.json()
            except ValueError:
                raise PipelineError("Edge Impulse a renvoyé une réponse JSON illisible.") from None
            if not isinstance(body, dict) or body.get("success", True) is not True:
                raise PipelineError(f"{method} signalé en échec par Edge Impulse.")
            return body
        raise PipelineError("Requête incomplète.")

    def studio(self, method, endpoint="", **kwargs):
        return self.request(method, f"{STUDIO}/api/{self.project_id}{endpoint}", **kwargs)

    def check_project(self):
        project = self.studio("GET")["project"]
        if (project["id"] != self.project_id or project["name"] != self.project_name
                or project.get("isPublic") is not False):
            raise PipelineError("Le projet retourné ne correspond pas au projet privé demandé.")
        return {"id": project["id"], "name": project["name"], "private": True}

    def pages(self, endpoint, field, **params):
        offset = 0
        total = None
        while total is None or offset < total:
            body = self.studio("GET", endpoint, params={**params, "offset": offset, "limit": 100})
            batch = body[field]
            count = body["totalCount"]
            if (total is not None and total != count) or (not batch and offset < count):
                raise PipelineError("Inventaire distant modifié ou pagination incomplète.")
            total = count
            yield body
            offset += len(batch)
        if offset != total:
            raise PipelineError("Le nombre d’éléments reçus diffère du total annoncé.")

    def inventory(self, category):
        return [
            item for page in self.pages("/raw-data", "samples", category=category)
            for item in page["samples"]
        ]

    def upload(self, path, row, category):
        metadata = {key: row[key] for key in (
            "sample_id", "split", "speaker_id", "source_file", "source_noise", "augmentation", "snr_db", "sha256",
        )}
        with path.open("rb") as stream:
            result = self.request(
                "POST", f"{INGESTION}/api/{category}/files",
                headers={"x-label": row["label"], "x-metadata": json.dumps(metadata)},
                files={"data": (path.name, stream, "audio/wav")},
            )
        files = result.get("files", [])
        if len(files) != 1 or files[0].get("success") is not True:
            raise PipelineError(f"Import refusé pour {row['sample_id']}, vérifiez le fichier dans Studio.")
        return files[0]

    def start(self, endpoint, payload, **params):
        body = self.studio("POST", f"/jobs/{endpoint}", json=payload, params=params)
        job_id = body["id"]
        print(f"Job {job_id} lancé, utilisez status pour reprendre son suivi.", flush=True)
        return body

    def wait(self, job_id, timeout=1200, interval=3):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            job = self.studio("GET", f"/jobs/{job_id}/status")["job"]
            if job.get("finished"):
                if job.get("finishedSuccessful") is True:
                    return
                raise PipelineError(f"Job {job_id} terminé en échec ou annulé. Consultez son journal dans Studio.")
            time.sleep(min(interval, max(0, deadline - time.monotonic())))
        raise PipelineError(f"Délai de suivi dépassé, job {job_id}. Reprenez avec status.")

    def predictions(self, impulse):
        result, predictions = [], []
        for page in self.pages("/classify/all/result/page", "result",
                               category="testing", variant="int8", impulseId=impulse):
            result.extend(page["result"])
            predictions.extend(page["predictions"])
        ids = [row["sampleId"] for row in result]
        if len(ids) != len(set(ids)):
            raise PipelineError("Le même échantillon apparaît sur plusieurs pages.")
        return {"success": True, "result": result, "predictions": predictions, "totalCount": len(ids)}

    def export(self, impulse, out):
        targets = self.studio("GET", "/deployment/targets", params={"impulseId": impulse})["targets"]
        arduino = next((target for target in targets if target["name"] == "Arduino library"
                        and not target.get("disabledForProject")
                        and "tflite-eon" in target["supportedEngines"]), None)
        if arduino is None:
            raise PipelineError("Cible Arduino EON indisponible. Vérifiez Deployment dans Studio.")
        job = self.start("build-ondevice-model", {"engine": "tflite-eon", "modelType": "int8"},
                         type=arduino["format"], impulseId=impulse)
        version = job["deploymentVersion"]
        print(f"Déploiement Studio {version}.", flush=True)
        self.wait(job["id"])
        self.download(version, out)

    def download(self, version, out):
        blob = self.studio("GET", f"/deployment/history/{version}/download", binary=True)
        validate_zip(blob)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("xb") as stream:
            stream.write(blob)


def validate_zip(blob):
    try:
        with zipfile.ZipFile(BytesIO(blob)) as archive:
            if archive.testzip() is not None:
                raise PipelineError("Le ZIP Arduino est corrompu.")
            metas = [name for name in archive.namelist() if name.endswith("/model_metadata.h")]
            if not any(name.endswith("/library.properties") for name in archive.namelist()) or len(metas) != 1:
                raise PipelineError("Le ZIP ne correspond pas à une bibliothèque Arduino.")
            metadata = archive.read(metas[0]).decode("utf-8")
            if not all(re.search(rf"^#define\s+EI_CLASSIFIER_TFLITE_{name}_DATATYPE\s+EI_CLASSIFIER_DATATYPE_INT8\b",
                                 metadata, re.MULTILINE) for name in ("INPUT", "OUTPUT")):
                raise PipelineError("L’export ne contient pas les tenseurs d’entrée et de sortie INT8 attendus.")
            return metadata
    except (zipfile.BadZipFile, UnicodeError):
        raise PipelineError("Archive Arduino illisible.") from None


def upload_plan(data, split):
    seen = set()
    selected = []
    for row in manifest_rows(data / "manifest.csv"):
        if row["split"] != split:
            continue
        name = row["sample_id"]
        if not re.fullmatch(r"[a-z0-9.-]+", name) or row["label"] not in LABELS or name in seen:
            raise PipelineError(f"Identifiant ou étiquette invalide dans {split}.")
        seen.add(name)
        path = data / split / f"{name}.wav"
        if file_sha256(path) != row["sha256"]:
            raise PipelineError(f"Empreinte WAV incorrecte pour {name}.")
        selected.append((path, row))
    if not selected:
        raise PipelineError(f"Aucun clip dans {split}.")
    return selected


def send_samples(client, plan, category):
    inventory = {}
    for partition in ("training", "testing"):
        for sample in client.inventory(partition):
            inventory.setdefault(sample["filename"], []).append((partition, sample))
    pending, skipped = [], []
    for path, row in plan:
        name = row["sample_id"]
        matches = inventory.get(name, [])
        if not matches:
            pending.append((path, row))
            continue
        if len(matches) != 1:
            raise PipelineError(f"Plusieurs clips distants portent le nom {name}.")
        remote_category, sample = matches[0]
        if (remote_category != category or sample["label"] != row["label"]
                or (sample.get("metadata") or {}).get("sha256") != row["sha256"]):
            raise PipelineError(f"Clip distant non réconcilié pour {name}. Contrôlez son origine dans Studio.")
        skipped.append(name)
    print(f"{len(skipped)} clips déjà vérifiés, {len(pending)} à importer.", flush=True)
    for index, (path, row) in enumerate(pending, 1):
        client.upload(path, row, category)
        print(f"{index}/{len(pending)} : {row['sample_id']} accepté", flush=True)


def gate_report(baseline, candidate, policy, hardware=None):
    if policy["schema_version"] != 1 or policy["evaluation"] != {
        "clean_split": SPLITS[0], "shifted_split": SPLITS[1],
        "uncertain_counts_as_miss": True, "false_trigger_condition": "each",
    }:
        raise PipelineError("Politique de promotion incompatible avec le calcul des métriques.")
    if baseline["manifest_sha256"] != candidate["manifest_sha256"]:
        raise PipelineError("Les deux rapports proviennent de manifestes différents.")
    reference = baseline["splits"]
    current = candidate["splits"]
    clean, shifted = (current[split] for split in SPLITS)
    if any(current[split]["n"] <= 0 or current[split]["n"] != reference[split]["n"] for split in SPLITS):
        raise PipelineError("Les effectifs d’évaluation diffèrent entre expériences.")
    checks = []

    def metric(name, value, limit, operator):
        if not math.isfinite(value) or not math.isfinite(limit):
            raise PipelineError(f"Valeur non finie pour {name}.")
        within_rounding = math.isclose(value, limit, rel_tol=0, abs_tol=1e-12)
        ok = within_rounding or (value >= limit if operator == ">=" else value <= limit)
        checks.append(dict(criterion=name, value=value, operator=operator, limit=limit, status="ok" if ok else "failed"))

    metric("accuracy_clean", clean["accuracy"], policy["accuracy_clean_min"], ">=")
    for label in ("go", "stop"):
        metric(f"recall_{label}_clean", clean[f"recall_{label}"], policy["command_recall_clean_min"], ">=")
    metric("macro_f1_shifted_gain", shifted["macro_f1"] - reference[SPLITS[1]]["macro_f1"],
           policy["macro_f1_shifted_gain_min"], ">=")
    metric("macro_f1_clean_loss", reference[SPLITS[0]]["macro_f1"] - clean["macro_f1"],
           policy["macro_f1_clean_loss_max"], "<=")
    for split in SPLITS:
        metric(f"false_trigger_{split}", current[split]["false_trigger_rate"],
               policy["noise_false_trigger_rate_max"], "<=")
    offline_passed = all(check["status"] == "ok" for check in checks)
    for criterion in ("firmware_compile", "firmware_init", "measured_acquisition_budget"):
        if policy[f"require_{criterion}"]:
            value = (hardware or {}).get(criterion)
            status = "ok" if value is True else "failed" if value is False else "pending"
            checks.append(dict(criterion=criterion, value=value, operator="==", limit=True, status=status))
    statuses = {check["status"] for check in checks}
    decision = "rejected" if "failed" in statuses else "pending" if "pending" in statuses else "accepted"
    return {"decision": decision, "offline_passed": offline_passed, "checks": checks}


def release_manifest(args):
    with args.archive.open("rb") as archive:
        metadata = validate_zip(archive.read())
    for field, expected in (("PROJECT_ID", args.project), ("PROJECT_DEPLOY_VERSION", args.deployment_version)):
        pattern = rf"^#define\s+EI_CLASSIFIER_{field}\s+{expected}\s*$"
        if not re.search(pattern, metadata, re.MULTILINE):
            raise PipelineError(f"L’identité {field} du ZIP diffère de celle demandée.")
    candidate = read_json(args.candidate)
    decision = read_json(args.report)
    if decision.get("injection"):
        raise PipelineError("Un rapport d’injection ne peut pas être archivé comme résultat réel.")
    dataset_hash = file_sha256(args.manifest)
    if (candidate["manifest_sha256"] != dataset_hash or decision["manifest_sha256"] != dataset_hash
            or decision["candidate_sha256"] != file_sha256(args.candidate)):
        raise PipelineError("Le rapport de décision ne correspond pas aux métriques ou au manifeste.")
    git = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=LAB, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=LAB))
    write_json(args.out, {
        "schema_version": 1, "version": args.version, "project_id": args.project,
        "impulse_id": args.impulse, "deployment_version": args.deployment_version,
        "target": {"board": "ABX00031", "fqbn": "arduino:mbed_nano:nano33ble"},
        "engine": "tflite-eon", "variant": "int8", "git_commit": git, "git_dirty": dirty,
        "dataset_sha256": dataset_hash, "arduino_zip_sha256": file_sha256(args.archive),
        "metrics_sha256": file_sha256(args.candidate), "gates_sha256": file_sha256(args.report),
        "decision": decision["decision"], "firmware": None, "stage": "candidate-package",
    })


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=int)
    parser.add_argument("--name", help="nom Studio exact du projet privé")
    parser.add_argument("--apply", action="store_true", help="autorise la mutation prévue dans Studio")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check")
    upload = commands.add_parser("upload")
    upload.add_argument("split", choices=UPLOAD_SPLITS)
    upload.add_argument("--data", type=Path, default=DEFAULT_DATA)
    status = commands.add_parser("status")
    status.add_argument("job", type=int)
    features = commands.add_parser("features")
    features.add_argument("dsp", type=int)
    train = commands.add_parser("train")
    train.add_argument("learn", type=int)
    for name in ("classify", "results", "export"):
        command = commands.add_parser(name)
        command.add_argument("impulse", type=int)
        if name != "classify":
            command.add_argument("out", type=Path)
    download = commands.add_parser("download")
    download.add_argument("deployment_version", type=int)
    download.add_argument("out", type=Path)
    gate = commands.add_parser("gate")
    for value in ("baseline", "candidate", "out"):
        gate.add_argument(value, type=Path)
    gate.add_argument("--policy", type=Path, default=LAB / "config/quality-gates.json")
    gate.add_argument("--hardware", type=Path)
    gate.add_argument("--inject-false-trigger", action="store_true", help="essai de rejet fictif, sans modifier les entrées")
    package = commands.add_parser("manifest")
    package.add_argument("version")
    package.add_argument("impulse", type=int)
    package.add_argument("deployment_version", type=int)
    for value in ("archive", "manifest", "candidate", "report", "out"):
        package.add_argument(value, type=Path)
    return parser.parse_args()


def run(args):
    command = args.command
    if command == "gate":
        policy, baseline, candidate = (read_json(path) for path in (args.policy, args.baseline, args.candidate))
        if args.out.exists():
            raise PipelineError("Le rapport existe déjà. Choisissez un nouveau fichier.")
        evaluated = deepcopy(candidate) if args.inject_false_trigger else candidate
        if args.inject_false_trigger:
            evaluated["splits"][SPLITS[1]]["false_trigger_rate"] = 1.0
        report = gate_report(baseline, evaluated, policy, read_json(args.hardware) if args.hardware else None)
        if args.inject_false_trigger:
            report["injection"] = "pédagogique : faux déclenchements dégradés forcés à 100 %"
        report.update(policy_sha256=file_sha256(args.policy), baseline_sha256=file_sha256(args.baseline),
                      candidate_sha256=file_sha256(args.candidate), manifest_sha256=candidate["manifest_sha256"])
        write_json(args.out, report)
        print(f"Décision {report['decision']}. Rapport dans {args.out}.")
        return 0 if report["decision"] == "accepted" else 2 if report["decision"] == "rejected" else 3
    if command == "manifest":
        if not args.project:
            raise PipelineError("Indiquez --project pour la provenance du manifeste.")
        if args.out.exists():
            raise PipelineError("Le manifeste existe déjà. Choisissez un nouveau fichier.")
        release_manifest(args)
        print(f"Manifeste candidat écrit dans {args.out}.")
        return 0

    if not args.project or not args.name:
        raise PipelineError("Indiquez --project et --name pour identifier le projet.")
    plan = upload_plan(args.data, args.split) if command == "upload" else None
    actions = {
        "features": ("generate-features", {"dspId": getattr(args, "dsp", None)}, {}),
        "train": (f"train/keras/{getattr(args, 'learn', None)}", {}, {}),
        "classify": ("classify", {"modelVariants": ["int8"]},
                     {"impulseId": getattr(args, "impulse", None), "category": "testing"}),
    }
    if hasattr(args, "out") and args.out.exists():
        raise PipelineError("Le dossier ou fichier de sortie existe déjà. Choisissez un nouveau chemin.")
    mutating = command in {"upload", "features", "train", "classify", "export"}
    if mutating and not args.apply:
        operation = (f"{len(plan)} WAV de {args.split} vers {UPLOAD_SPLITS[args.split]}" if plan is not None else
                     f"export Arduino EON INT8 de l’expérience {args.impulse}" if command == "export" else
                     f"job {actions[command][0]} {actions[command][1] or ''} {actions[command][2] or ''}")
        print(f"Dry-run · projet {args.project} « {args.name} » · {operation}")
        return 0

    client = EdgeImpulse(args.project, args.name, os.getenv("EI_API_KEY"))
    project = client.check_project()
    if command == "check":
        print(json.dumps(project, ensure_ascii=False))
    elif command == "upload":
        send_samples(client, plan, UPLOAD_SPLITS[args.split])
    elif command in actions:
        endpoint, payload, params = actions[command]
        client.wait(client.start(endpoint, payload, **params)["id"])
    elif command == "status":
        client.wait(args.job)
        print(f"Job {args.job} terminé avec succès.")
    elif command == "results":
        results = client.predictions(args.impulse)
        write_json(args.out, results)
        print(f"{len(results['result'])} résultats INT8 enregistrés.")
    elif command == "export":
        client.export(args.impulse, args.out)
        print(f"ZIP Arduino INT8 écrit dans {args.out}.")
    elif command == "download":
        client.download(args.deployment_version, args.out)
        print(f"ZIP Arduino INT8 écrit dans {args.out}.")
    return 0


def main():
    try:
        return run(arguments())
    except (PipelineError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        # Les messages du transport n’incluent jamais la réponse brute ou la clé.
        hint = str(error) if isinstance(error, (PipelineError, OSError)) else "Format de données ou configuration invalide."
        print(f"Erreur : {hint}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrompu. Vérifiez les jobs ou les imports avant toute reprise.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
