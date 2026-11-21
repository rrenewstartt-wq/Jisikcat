"""Prepare the pinned camera footage and the two browser scene inputs."""

import csv
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "work"


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def main():
    clips = WORK / "footage"
    clips.mkdir(exist_ok=True, parents=True)
    for asset in json.loads((ROOT / "footage.json").read_text()):
        target = clips / asset["file"]
        if target.exists() and digest(target) == asset["sha256"]:
            continue
        temp = target.with_suffix(".part")
        request = urllib.request.Request(
            asset["download"], headers={"User-Agent": "Jisikcat film production"}
        )
        with (
            urllib.request.urlopen(request, timeout=90) as response,
            temp.open("wb") as file,
        ):
            shutil.copyfileobj(response, file)
        if digest(temp) != asset["sha256"]:
            raise ValueError(f"촬영본 버전을 확인하세요: {target.name}")
        temp.replace(target)
    with (ROOT.parents[1] / "assets/prices.csv").open() as dataset:
        prices = [float(row["EUR_per_MWh"]) for row in csv.DictReader(dataset)]
    (WORK / "prices.json").write_text(json.dumps(prices))
    gsap = ROOT / "node_modules/gsap/dist/gsap.min.js"
    if gsap.is_file():
        shutil.copyfile(gsap, ROOT / "tariff/gsap.min.js")


if __name__ == "__main__":
    main()
