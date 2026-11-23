"""Download the public grammar test sets into data/public. Never committed: check each set's terms."""

import io
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "data"
PUBLIC = ROOT / "public"
PERSONAL = ROOT / "personal"

SETS = {
    "conll14": {
        "url": "https://www.comp.nus.edu.sg/~nlp/conll14st/conll14st-test-data.tar.gz",
        "member": "official-2014.combined.m2",
        "terms": "CoNLL-2014 shared task test data (NUS). For research use; see the shared task page.",
    },
    "bea19dev": {
        "url": "https://www.cl.cam.ac.uk/research/nl/bea2019st/data/wi+locness_v2.1.bea19.tar.gz",
        "member": "ABCN.dev.gold.bea19.m2",
        "terms": "W&I+LOCNESS v2.1 (BEA-2019). Non-commercial research licence; see the BEA-2019 page.",
    },
}


def m2_path(name: str) -> Path:
    return PUBLIC / f"{name}.m2"


def download(name: str) -> Path:
    spec = SETS[name]
    out = m2_path(name)
    if out.exists():
        return out
    PUBLIC.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(spec["url"], headers={"User-Agent": "redline-eval"})
    with urllib.request.urlopen(req, timeout=120) as r:
        blob = r.read()
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        member = next(m for m in tar.getmembers() if m.name.endswith(spec["member"]))
        out.write_bytes(tar.extractfile(member).read())
    print(f"{name}: saved {out}\n  terms: {spec['terms']}")
    return out


def download_all() -> None:
    for name in SETS:
        download(name)
