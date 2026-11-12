"""Unit tests for build_index.py (stdlib unittest; run: python3 -m unittest -v test_build_index)."""
import json
import tempfile
import unittest
from pathlib import Path

import build_index

TAXONOMY = {"version": 2, "scenarios": {
    "single-cell": {"label": "单细胞分析", "aliases": ["单细胞", "Seurat"]},
    "transcriptomics": {"label": "转录组", "aliases": ["RNA-seq"]},
}}


def row(i, **extra):
    base = {"id": f"r{i}", "kind": "recipe", "title": f"配方{i}", "page": f"recipes/r{i}.md",
            "chart_types": ["heatmap"], "tags": ["single-cell"], "language": "r",
            "requires": ["pheatmap", "knitr"], "keywords": ["k"], "summary": "s"}
    base.update(extra)
    return base


class BuildIndexTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.wiki = Path(self.tmp.name)
        self.taxonomy = self.wiki / "taxonomy.yaml"
        self.taxonomy.write_text(json.dumps(TAXONOMY, ensure_ascii=False), encoding="utf-8")
        (self.wiki / "chart-types").mkdir()
        (self.wiki / "chart-types" / "heatmap.md").write_text("---\ntype: chart-type\nslug: heatmap\ntitle: 热图\n---\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, rows, raw_lines=()):
        lines = [json.dumps(r, ensure_ascii=False) for r in rows] + list(raw_lines)
        (self.wiki / "catalog.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return build_index.build_index(self.wiki / "catalog.jsonl", self.taxonomy, self.wiki / "chart-types")

    def test_entry_count_follows_catalog(self):
        for n in (3, 17):  # count is read, never assumed; growth shows up after rebuild
            index = self.build([row(i) for i in range(n)])
            self.assertEqual(index["stats"]["entries"], n)
            self.assertEqual(len(index["entries"]), n)
            self.assertEqual(index["facets"]["charts"], [{"value": "heatmap", "count": n}])

    def test_missing_and_malformed_fields(self):
        bare = {"id": "bare"}
        odd = {"id": "odd", "tags": "转录组", "chart_types": None, "requires": [1, " ", "ggplot2"], "title": 5}
        index = self.build([bare, odd], raw_lines=["", "not json", "[1,2]"])
        by_id = {e["id"]: e for e in index["entries"]}
        self.assertEqual(index["stats"]["entries"], 2)
        self.assertEqual(index["stats"]["skipped_lines"], [4, 5])
        self.assertEqual(by_id["bare"]["title"], "bare")
        self.assertEqual(by_id["bare"]["charts"], [])
        self.assertEqual(by_id["bare"]["packages"], [])
        self.assertEqual(by_id["bare"]["page"], "")
        self.assertEqual(by_id["odd"]["domains"], ["transcriptomics"])  # bare string tag accepted
        self.assertEqual(by_id["odd"]["packages"], ["ggplot2"])

    def test_tags_normalised_to_vocabulary_keys(self):
        index = self.build([row(1, tags=["单细胞分析", "single-cell", "RNA-seq", "空间组"])])
        entry = index["entries"][0]
        self.assertEqual(entry["domains"], ["single-cell", "transcriptomics"])
        self.assertEqual(entry["unknown_tags"], ["空间组"])
        self.assertEqual(index["facets"]["unknown_tags"], [{"value": "空间组", "count": 1}])
        self.assertIn("单细胞分析", entry["_text"])  # label searchable even when the tag is a key

    def test_packages_only_for_r_and_without_boilerplate(self):
        index = self.build([row(1), row(2, language="python", requires=["numpy"])])
        by_id = {e["id"]: e for e in index["entries"]}
        self.assertEqual(by_id["r1"]["packages"], ["pheatmap"])
        self.assertEqual(by_id["r2"]["packages"], [])

    def test_unknown_chart_flagged(self):
        entry = self.build([row(1, chart_types=["heatmap", "sunburst"])])["entries"][0]
        self.assertEqual(entry["unknown_charts"], ["sunburst"])

    def test_cli_writes_json_and_reads_only(self):
        self.build([row(1)])
        before = (self.wiki / "catalog.jsonl").read_bytes()
        out = self.wiki / "out.json"
        code = build_index.main(["--wiki", str(self.wiki), "--taxonomy", str(self.taxonomy), "--out", str(out)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["stats"]["entries"], 1)
        self.assertEqual((self.wiki / "catalog.jsonl").read_bytes(), before)
        self.assertEqual(build_index.main(["--wiki", str(self.wiki / "nope"), "--taxonomy", str(self.taxonomy)]), 2)


if __name__ == "__main__":
    unittest.main()
