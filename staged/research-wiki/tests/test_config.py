import json
import sys

import pytest

from rwiki.config import load_config
from rwiki.errors import WikiError


@pytest.mark.parametrize("missing", ["python_exe", "rscript_exe", "port"])
def test_missing_runtime_key_is_error(tmp_path, missing):
    values = {key: str(tmp_path) for key in ("wiki_root", "gallery_root", "taxonomy")}
    values.update(python_exe=sys.executable,
                  rscript_exe="D:/R-4.5.0/bin/Rscript.exe")
    values["port"] = 8765
    del values[missing]
    path = tmp_path / "config.json"
    path.write_text(json.dumps(values), encoding="utf-8")
    with pytest.raises(WikiError, match=missing):
        load_config(path)
