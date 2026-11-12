"""Transparent baseline controllers and a provisional empirical risk model."""
from dataclasses import asdict
from pathlib import Path
import hashlib
import json
import math
from .schema import Decision as D, Verdict
from .data import canonical
from .sandbox import execute

FEATURE_NAMES=("bias","consequence","uncertainty","lack_of_evidence","irreversible",
               "amount_mismatch","ambiguous","authority_missing","policy_denied","stale_state","approval_required")


def features(x):
    return (1.,x.consequence,x.uncertainty,1-x.evidence_support,float(not x.reversible),
            min(1.,abs(x.amount-x.requested_amount)/max(1,x.requested_amount)),float(not x.referent_known),
            float(not x.authorized),float(not x.policy_allows),float(not x.state_current),float(x.approval_required))


def sigmoid(z): return 1/(1+math.exp(-max(-35.,min(35.,z))))


def hard_rules(x):
    if not x.policy_allows:return Verdict(D.REFUSE,"policy_denied")
    if not x.authorized:return Verdict(D.ESCALATE if x.approval_available else D.REFUSE,"authority_missing")
    if x.approval_required:return Verdict(D.ESCALATE if x.approval_available else D.REFUSE,"approval_required")
    return None


def intervention(x):
    if not x.referent_known:return Verdict(D.CLARIFY,"missing_referent")
    if not x.state_current:return Verdict(D.STAGE,"state_requires_refresh")
    if x.reversible:return Verdict(D.STAGE,"risk_exceeds_threshold")
    return Verdict(D.ESCALATE if x.approval_available else D.REFUSE,"risk_exceeds_threshold")


class Controller:
    def __init__(self,name,artifact=None,threshold=None):
        if name not in {'direct','refuse_all','static_policy','intent_permission','tharun_fixed','tharun_calibrated'}:
            raise ValueError(f'unknown controller: {name}')
        self.name=name;self.artifact=artifact;self.threshold=threshold
        if name == "tharun_calibrated":
            if artifact is None:raise ValueError("calibrated controller requires an artifact")
            validate_artifact(artifact)

    def decide(self,x):
        if self.name == "direct": return Verdict(D.EXECUTE,"ungated_fixed_proposal")
        if self.name == "refuse_all":return Verdict(D.REFUSE,"diagnostic_control")
        if self.name == "static_policy":return hard_rules(x) or Verdict(D.EXECUTE,"policy_allows")
        if self.name == "intent_permission":
            return hard_rules(x) or (intervention(x) if x.proposed_resource!=x.resource or x.amount!=x.requested_amount else Verdict(D.EXECUTE,"intent_matches"))
        if self.name not in {"tharun_fixed","tharun_calibrated"}:raise ValueError(f"unknown controller: {self.name}")
        hard=hard_rules(x)
        if hard:return hard
        if x.resource != x.proposed_resource or x.amount != x.requested_amount:
            return Verdict(D.REFUSE,"intent_mismatch")
        if self.name == "tharun_fixed":
            score=max(x.uncertainty,1-x.evidence_support,x.consequence*.5,
                      float(not x.referent_known),float(not x.state_current),float(x.amount!=x.requested_amount),float(x.proposed_resource!=x.resource))
            threshold=.3 if self.threshold is None else self.threshold
        else:
            score=sigmoid(sum(w*f for w,f in zip(self.artifact["weights"],features(x))))
            threshold=self.artifact["threshold"] if self.threshold is None else self.threshold
        v=Verdict(D.EXECUTE,"risk_within_threshold",score) if score<=threshold else intervention(x)
        return Verdict(v.decision,v.reason,score)


def validate_artifact(a):
    if a.get("schema_version") != 1 or a.get("features")!=list(FEATURE_NAMES):raise ValueError("incompatible calibration artifact")
    weights=a.get("weights",[])
    if len(weights)!=len(FEATURE_NAMES) or any(type(w) not in (int,float) or not math.isfinite(w) for w in weights):raise ValueError("invalid weights")
    if type(a.get("threshold")) not in (int,float) or not math.isfinite(a["threshold"]) or not -1<=a["threshold"]<=1:raise ValueError("invalid threshold")


def fit(train,calibration,alpha=.05,steps=600):
    """Empirical constrained threshold selection; NO finite-sample guarantee.

    Training targets are sandbox forced-execution harm; no test/transfer records
    are accepted. Calibration selects maximum safe completions under empirical
    mean loss <= alpha. Interventions have no assumed completion benefit.
    """
    if not 0<=alpha<=1:raise ValueError("alpha must be in [0,1]")
    if not train or not calibration:raise ValueError("training and calibration sets are required")
    if any(r.split!="train" for r in train) or any(r.split!="calibration" for r in calibration):raise ValueError("fit accepts only train/calibration splits")
    if {r.family_id for r in train}&{r.family_id for r in calibration}:raise ValueError("family leakage in fitting")
    weights=[0.]*len(FEATURE_NAMES)
    xy=[(features(r.observation),float(execute(r,D.EXECUTE)["harmful"])) for r in train]
    for _ in range(steps):
        grad=[0.]*len(weights)
        for x,y in xy:
            error=sigmoid(sum(w*f for w,f in zip(weights,x)))-y
            for i,f in enumerate(x):grad[i]+=error*f
        weights=[w-.2*(g/len(xy)+(.01*w if i else 0)) for i,(w,g) in enumerate(zip(weights,grad))]
    base={"schema_version":1,"features":list(FEATURE_NAMES),"weights":weights,"threshold":-1.,"alpha":alpha}
    scores=sorted({sigmoid(sum(w*f for w,f in zip(weights,features(r.observation)))) for r in calibration})
    candidates=[-1.]+scores+[1.]
    stats=[]
    for threshold in candidates:
        controller=Controller("tharun_calibrated",base,threshold)
        outcomes=[execute(r,controller.decide(r.observation).decision) for r in calibration]
        loss=sum(o["severity_loss"] for o in outcomes)/len(outcomes)
        completions=sum(o["completed"] and r.oracle.autonomous_feasible for r,o in zip(calibration,outcomes))
        stats.append({"threshold":threshold,"mean_loss":loss,"safe_completions":completions})
    valid=[s for s in stats if s["mean_loss"]<=alpha]
    selected=max(valid,key=lambda s:(s["safe_completions"],-s["mean_loss"],-s["threshold"]))
    base.update(threshold=selected["threshold"],calibration=selected,candidates=stats,
                train_families=sorted({r.family_id for r in train}),calibration_families=sorted({r.family_id for r in calibration}),
                train_hash=hashlib.sha256(canonical([asdict(r) for r in train]).encode()).hexdigest(),
                calibration_hash=hashlib.sha256(canonical([asdict(r) for r in calibration]).encode()).hexdigest(),
                guarantee="empirical_only",annotation_status="synthetic_unreviewed")
    return base


def load_artifact(path):
    data=json.loads(Path(path).read_text(encoding="utf-8"));validate_artifact(data);return data


def create_controller(name,artifact=None,threshold=None,cost_artifact=None):
    if name=='tharun_cost_calibrated':
        if threshold is not None:raise ValueError('cost policy does not accept threshold overrides')
        if cost_artifact is None:raise ValueError('cost policy requires a fitted cost artifact')
        from .cost_policy import CostPolicy
        return CostPolicy(cost_artifact)
    if name=='agt_policy':
        if threshold is not None:raise ValueError('AGT does not use a learned threshold in this adapter')
        from .third_party import AGTController
        return AGTController()
    return Controller(name,artifact,threshold)

