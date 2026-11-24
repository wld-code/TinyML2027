#!/usr/bin/env bash
# Étape 10 (TP01) : session guidée courte w01, journal complet dans evidence/windows/10_capture_guided_w01.txt
cd "$(dirname "$0")/../.."
export PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1
{ echo '$ uv run python -m tinyml2027.capture guided --session w01'; } > evidence/windows/10_capture_guided_w01.txt
uv run python -m tinyml2027.capture guided --session w01 2>&1 | tee -a evidence/windows/10_capture_guided_w01.txt
echo "EXIT=${PIPESTATUS[0]}" | tee -a evidence/windows/10_capture_guided_w01.txt
