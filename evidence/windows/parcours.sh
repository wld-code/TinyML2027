#!/usr/bin/env bash
# Parcours « sans carte » sur PC Windows (Git Bash), après ./scripts/setup.sh.
# Chaque étape : OK/ECHEC + durée ; journal complet dans evidence/windows/<étape>.log.
# Lancer depuis la racine du dépôt : bash evidence/windows/parcours.sh
set -uo pipefail
OUT=evidence/windows
step() { local name="$1"; shift; local t0=$SECONDS; local log="$OUT/$(echo "$name" | tr ' /' '__').log"
  echo; echo "=== $name"
  if bash -o pipefail -c "$*" > "$log" 2>&1; then echo "OK ($((SECONDS-t0)) s)"
  else echo "ECHEC ($((SECONDS-t0)) s) — fin du journal :"; tail -25 "$log"; fi; }
step "02 tuto01 notebooks" uv run pytest -q --nbmake tutorials/01-python-jupyter
step "03 tests" uv run pytest -q
step "04-08 tuto02 compilation" 'set -e; for s in examples/01_blink tutorials/02-arduino-nano/sketches/board_identify advanced/edge-impulse/sketches/mic_check; do ./scripts/compile.sh $s | tail -2; done; for s in examples/04_imu labs/01-sensor-data/firmware/imu_capture; do REV=original ./scripts/compile.sh $s | tail -2; REV=rev2 ./scripts/compile.sh $s | tail -2; done'
step "09 exemples 03 05" 'set -e; uv run python python/train.py; uv run python python/convert.py --mode fp32; ./scripts/compile.sh examples/03_custom_model | tail -2; uv run python python/convert.py --mode int8; ./scripts/compile.sh examples/05_int8_model | tail -2'
step "11 TP01 features" uv run python -m tinyml2027.build_features --data datasets/motion-nano-v1
step "12 TP02 entrainement" uv run python -m tinyml2027.train_motion --test-session s05
step "13 TP03 int8 cpp firmware" 'set -e; uv run python -m tinyml2027.quantize_motion --data datasets/motion-nano-v1; uv run pytest -q tests/test_features_cpp.py; REV=original ./scripts/compile.sh labs/03-embedded-inference/firmware/infer_nano | tail -2; REV=rev2 ./scripts/compile.sh labs/03-embedded-inference/firmware/infer_nano | tail -2'
echo; echo "=== RÉSUMÉ"; cmd //c ver | tr -d '\r' | grep -v '^$'; uname -sm
uv run python -c "
import json,hashlib,pathlib
d=json.loads(pathlib.Path('artifacts/motion/metrics.json').read_text()); t=d['test']['dense']
print('TP02 test s05 : accuracy %.3f macro-F1 %.3f ; CV %.3f' % (t['accuracy'], t['macro_f1'], d['cv_train']['dense']['macro_f1_mean']))
q=pathlib.Path('artifacts/motion/model_int8.tflite'); print('INT8', q.stat().st_size, 'octets sha256', hashlib.sha256(q.read_bytes()).hexdigest()[:16])
" 2>&1 | tail -3
cp build/*.log "$OUT"/ 2>/dev/null; true
