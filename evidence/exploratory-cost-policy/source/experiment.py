"""Versioned append-only run records and local fixed-proposal evaluation."""
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
import hashlib
import json
import platform
import shutil
import time
import uuid
from . import __version__
from .data import canonical, sha256_file
from .metrics import summarize
from .sandbox import execute


class RunWriter:
    def __init__(self,path,manifest):
        self.path=Path(path);self.path.mkdir(parents=True,exist_ok=False)
        self.manifest={**manifest,"schema_version":1,"run_id":str(uuid.uuid4()),"entry_point":"cli",
            "created_at":datetime.now(timezone.utc).isoformat(),"package_version":__version__,
            "python":platform.python_version(),"platform":platform.platform(),"status":"running",
            "experiment_type":"synthetic_fixed_proposal","annotation_status":"synthetic_unreviewed",
            "paid_api_spend_usd":0,"code_hashes":{p.name:sha256_file(p) for p in sorted(Path(__file__).parent.iterdir()) if p.suffix in {'.py','.yaml'}}}
        self.previous="0"*64;self.count=0
        (self.path/'source').mkdir()
        for source in Path(__file__).parent.iterdir():
            if source.suffix in {'.py','.yaml'}:shutil.copy2(source,self.path/'source'/source.name)
        self._manifest()

    def _manifest(self):
        (self.path/'manifest.json').write_text(json.dumps(self.manifest,indent=2),encoding="utf-8")

    def append(self,record):
        body={**record,"run_id":self.manifest["run_id"],"entry_point":"cli","sequence":self.count,"previous_hash":self.previous}
        digest=hashlib.sha256(canonical(body).encode()).hexdigest();body["record_hash"]=digest
        with (self.path/'outcomes.jsonl').open('a',encoding='utf-8') as f:f.write(canonical(body)+'\n')
        self.previous=digest;self.count+=1

    def finish(self,status="completed",error=None):
        self.manifest.update(status=status,records=self.count,final_record_hash=self.previous,error=error,
            finished_at=datetime.now(timezone.utc).isoformat())
        self._manifest()


def verify_log(path):
    path=Path(path);prev="0"*64;count=0;rows=[]
    for line in (path/'outcomes.jsonl').read_text(encoding='utf-8').splitlines():
        body=json.loads(line);digest=body.pop('record_hash')
        if body['previous_hash']!=prev or body['sequence']!=count or hashlib.sha256(canonical(body).encode()).hexdigest()!=digest:
            raise ValueError(f"invalid audit chain at record {count}")
        body['record_hash']=digest;rows.append(body);prev=digest;count+=1
    manifest=json.loads((path/'manifest.json').read_text(encoding='utf-8'))
    if manifest['records']!=count or manifest['final_record_hash']!=prev:raise ValueError("manifest/log mismatch")
    return rows


def evaluate(rows,controllers,writer,repeats=1,recovery="verify",max_seconds=None):
    if repeats<1:raise ValueError("repeats must be positive")
    start=time.monotonic();result=[]
    try:
        for controller in controllers:
            for repeat in range(repeats):
                if hasattr(controller,"seed"):controller.seed=23+repeat
                for row in rows:
                    if max_seconds is not None and time.monotonic()-start>max_seconds:
                        writer.finish("time_limit");return result
                    t=time.monotonic();verdict=controller.decide(row.observation)
                    elapsed=time.monotonic()-t
                    outcome=execute(row,verdict.decision,recovery=recovery)
                    record={"task_id":row.task_id,"family_id":row.family_id,"domain":row.domain,"variant":row.variant,
                        "split":row.split,"repeat":repeat,"system":controller.name,
                        "model":getattr(controller,"model",None),"threshold":getattr(controller,"threshold",None),
                        "inference_seed":getattr(controller,"seed",None),
                        "decision":verdict.decision.value,"reason":verdict.reason,"risk":verdict.risk,"error":verdict.error,
                        "decision_correct":verdict.decision in row.oracle.acceptable,
                        "autonomous_feasible":row.oracle.autonomous_feasible,"acceptable":[x.value for x in row.oracle.acceptable],
                        "latency_seconds":elapsed,"recovery_mode":recovery,"model_telemetry":getattr(controller,"last",{}),**outcome}
                    if 'intervention_costs' in writer.manifest:record['decision_cost']=writer.manifest['intervention_costs'][verdict.decision.value]
                    writer.append(record);result.append(record)
                    print(canonical({"event":"case_completed","run_id":writer.manifest["run_id"],"system":controller.name,
                        "model":getattr(controller,"model",None),"task_id":row.task_id,"decision":verdict.decision.value,
                        "error":verdict.error,"latency_seconds":round(elapsed,3)}),flush=True)
        writer.finish()
    except BaseException as exc:
        writer.finish("failed",type(exc).__name__);raise
    return result


def group_summary(rows):
    groups=defaultdict(list)
    for r in rows:groups[(r["system"],r["model"],r.get("threshold"))].append(r)
    return [{"system":system,"model":model,"threshold":threshold,**summarize(values)} for (system,model,threshold),values in groups.items()]


def select_balanced(rows,limit):
    """Deterministic variant round-robin; no oracle/performance-based selection."""
    if not limit or limit>=len(rows):return rows
    groups=defaultdict(list)
    for row in rows:groups[row.variant].append(row)
    # Interleave domains inside each variant before rotating, rather than taking
    # the first contiguous domain block. Selection never consults gold labels.
    for key,items in groups.items():
        domains=defaultdict(list)
        for row in items:domains[row.domain].append(row)
        names=sorted(domains)
        groups[key]=[domains[name][k] for k in range(max(map(len,domains.values())))
                     for name in names if k<len(domains[name])]
    result=[];keys=sorted(groups)
    for i in range(max(map(len,groups.values()))):
        for j,key in enumerate(keys):
            # Rotate domain/family choices across variant groups.
            ordered=groups[key];idx=(i+j)%len(ordered)
            if i<len(ordered):result.append(ordered[idx])
            if len(result)==limit:return result
    return result

