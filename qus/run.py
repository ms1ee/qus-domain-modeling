"""Phase 1 실행과 채점.

실행 기록: runs/phase1/<모델 이름>/<세트>/<입력>/rep<k>.json
이미 있는 기록은 건너뛰므로 중간에 끊겨도 같은 명령으로 이어서 돌릴 수 있다.
"""
import csv
import json
from datetime import datetime, timezone

from .config import ROOT, experiment_config, load_yaml
from .data import load_gold, load_stories
from .extract import extract
from .llm import make_client, role_models
from .score import Matcher, score_associations, score_classes

RUNS_DIR = ROOT / "runs" / "phase1"
RESULTS_DIR = ROOT / "results"


def load_input(set_id: str, input_id: str):
    if input_id == "original":
        return load_stories(set_id)
    raise NotImplementedError(f"입력 '{input_id}'는 노이즈 주입 단계 이후 지원")


def run_path(model_name: str, set_id: str, input_id: str, rep: int):
    return RUNS_DIR / model_name / set_id / input_id / f"rep{rep}.json"


def plan(inputs: list[str]) -> list[tuple]:
    cfg = experiment_config()
    return [(model_name, model_cfg, set_id, input_id, rep)
            for model_name, model_cfg in role_models("extractors").items()
            for set_id in cfg["sets"]
            for input_id in inputs
            for rep in range(1, cfg["repetitions"] + 1)]


def run(inputs: list[str], dry_run: bool = False) -> None:
    jobs = plan(inputs)
    todo = [j for j in jobs if not run_path(j[0], j[2], j[3], j[4]).exists()]
    print(f"{len(jobs)}개 실행 중 {len(jobs) - len(todo)}개 완료, {len(todo)}개 남음 (호출 최대 {2 * len(todo)}회)")
    if dry_run:
        for model_name, _, set_id, input_id, rep in todo:
            print(f"  {model_name} {set_id} {input_id} rep{rep}")
        return
    clients = {}
    for model_name, model_cfg, set_id, input_id, rep in todo:
        if model_name not in clients:
            clients[model_name] = make_client(model_cfg)
        record = extract(clients[model_name], load_input(set_id, input_id))
        record.update(model_name=model_name, model_config=model_cfg, set=set_id, input=input_id, rep=rep,
                      finished_at=datetime.now(timezone.utc).isoformat())
        path = run_path(model_name, set_id, input_id, rep)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  {model_name} {set_id} {input_id} rep{rep}: "
              f"classes={len(record['classes'] or [])} associations={len(record['associations'] or [])}"
              + (f" error={record['error']}" if record["error"] else ""))


FIELDS = ["model", "set", "input", "rep", "target", "tp", "fp", "fn", "dup", "precision", "recall", "f1",
          "collapsed", "out_of_list", "error"]


def score_all() -> None:
    gold, fixes = load_gold(), load_yaml("gold_fixes.yaml")
    rows = []
    for path in sorted(RUNS_DIR.glob("*/*/*/rep*.json")):
        r = json.loads(path.read_text(encoding="utf-8"))
        m = Matcher(r["set"], gold[r["set"]], fixes)
        base = {"model": r["model_name"], "set": r["set"], "input": r["input"], "rep": r["rep"],
                "error": r["error"] or ""}
        if r["classes"] is not None:
            rows.append({**base, "target": "classes", **score_classes(r["classes"], m)})
        if r["associations"] is not None:
            rows.append({**base, "target": "associations",
                         **score_associations(r["associations"], m, r["classes"])})
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / "phase1_scores.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)}행 → {out.relative_to(ROOT)}")
