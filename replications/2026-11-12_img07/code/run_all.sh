#!/usr/bin/env bash
# End-to-end img07 replica v2.2 run with receipt (runs/v2.2_<ts>.json), local test-gallery entry and qa_check.
# Usage: bash run_all.sh --obj OBJ.rds --tom TOM.rda --outroot DIR [--original PNG] [--v1 V1_REPLICA_PNG] [--skip_prepare 0|1]
set -uo pipefail
CMDLINE="bash $(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")$(printf " %q" "$@")"
CODE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL=/workspace/skills-sync/sci-figure-replica-github
ORIGINAL="$CODE_DIR/../source/full_original.png"; SKIP_PREP=0; V1=""; OBJ=""; TOM=""; OUTROOT=""
while [[ $# -gt 0 ]]; do case "$1" in
  --obj) OBJ="$2";; --tom) TOM="$2";; --outroot) OUTROOT="$2";; --original) ORIGINAL="$2";; --skip_prepare) SKIP_PREP="$2";; --v1) V1="$2";;
  *) echo "unknown arg $1"; exit 2;; esac; shift 2; done
[[ -n "$OBJ" && -n "$TOM" && -n "$OUTROOT" ]] || { echo "need --obj --tom --outroot"; exit 2; }
mkdir -p "$OUTROOT"/{data,output,compare,qa,runs,logs}
OUTROOT="$(cd "$OUTROOT" && pwd)"
TS="$(date +%Y%m%dT%H%M%S%z)"
source /home/box/miniforge3/etc/profile.d/conda.sh && conda activate rwiki-r
PY=/usr/bin/python3
STEPS="$OUTROOT/logs/steps_$TS.tsv"; echo -e "step\tcommand\tstart_epoch\tend_epoch\texit_code" > "$STEPS"
step() { local name="$1"; shift; local t0; t0=$(date +%s.%N)
  "$@" > "$OUTROOT/logs/${name}_$TS.log" 2>&1; local rc=$?
  echo -e "$name\t$*\t$t0\t$(date +%s.%N)\t$rc" >> "$STEPS"; echo "[$name] exit=$rc"; return $rc; }
free -h > "$OUTROOT/logs/free_before_$TS.txt"
if [[ "$SKIP_PREP" != "1" ]]; then
  step prepare Rscript "$CODE_DIR/01_prepare_network_go.R" --obj "$OBJ" --tom "$TOM" --outdir "$OUTROOT/data" || exit 1
fi
step plot Rscript "$CODE_DIR/02_plot_network_go.R" --datadir "$OUTROOT/data" --outdir "$OUTROOT/output" || exit 1
# display copy of the original converted from its embedded ICC profile (Display P3) to sRGB
ORIG_SRGB="$OUTROOT/compare/original_srgb.png"
step icc_to_srgb $PY "$CODE_DIR/icc_to_srgb.py" --in "$ORIGINAL" --out "$ORIG_SRGB" || exit 1
step compare $PY "$SKILL/scripts/make_compare.py" --original "$ORIG_SRGB" --replica "$OUTROOT/output/replica.png" \
  --out "$OUTROOT/compare/side_by_side.png" --overlay "$OUTROOT/compare/overlay.png" --footer "img07 replica v2.2 $TS (original shown converted P3->sRGB)"
if [[ -n "$V1" ]]; then
  step triptych $PY "$CODE_DIR/make_triptych.py" --images "$ORIG_SRGB" "$V1" "$OUTROOT/output/replica.png" \
    --labels "Original img07 (sRGB)" "Replica v1" "Replica v2.2" --out "$OUTROOT/compare/triptych_original_v1_v2.png"
fi
step measure_text $PY "$CODE_DIR/measure_text.py" "$ORIGINAL" "$OUTROOT/output/replica.png" --out "$OUTROOT/qa/text_measure_$TS.json"
step metrics $PY "$CODE_DIR/03_qa_metrics.py" --original "$ORIGINAL" --replica "$OUTROOT/output/replica.png" --out "$OUTROOT/qa/metrics_$TS.json"
MRC=$?
# local test gallery entry rebuilt from THIS run's outputs, then skill qa_check (never the real gallery)
GAL="$OUTROOT/gallery_local"; ENTRY="$GAL/ks-wgcna-scrna-bulk-20260810/figures/fig07"
rm -rf "$GAL"
step gallery_init $PY "$SKILL/scripts/init_entry.py" --gallery "$GAL" --post-slug ks-wgcna-scrna-bulk-20260810 --fig-id fig07 \
  --source "$ORIGINAL" --post-title "WGCNA：单细胞转录组+bulk RNA/蛋白组共表达网络分析" --post-url "https://mp.weixin.qq.com/s/LOpSnqiK3nfG-wVU8urzVw" \
  --account "KS生信科研课" --author "TS的美梦" --publish-date 2026-08-10 --language r --label img07 \
  --caption "hdWGCNA hub gene network + per-module GO enrichment bars (replica v2.2)" --chart-type network --chart-type bar \
  --data-provenance original --code-provenance reconstructed --original-code-provenance archived_only
step gallery_fill $PY "$CODE_DIR/fill_gallery_entry.py" --entry "$ENTRY" --outroot "$OUTROOT" --code_dir "$CODE_DIR" --ts "$TS"
step qa_check $PY "$SKILL/scripts/qa_check.py" --entry "$ENTRY" --original "$ORIGINAL" --replica "$OUTROOT/output/replica.png" --out "$ENTRY/qa_report.md"
cp "$ENTRY/qa_report.md" "$OUTROOT/qa/qa_check_mechanical.md"
free -h > "$OUTROOT/logs/free_after_$TS.txt"
step receipt $PY "$CODE_DIR/04_receipt.py" --outroot "$OUTROOT" --ts "$TS" --obj "$OBJ" --tom "$TOM" --original "$ORIGINAL" \
  --code_dir "$CODE_DIR" --steps "$STEPS" --metrics "$OUTROOT/qa/metrics_$TS.json" --cmdline "$CMDLINE"
echo "receipt: $OUTROOT/runs/v2.2_$TS.json"
exit $MRC
