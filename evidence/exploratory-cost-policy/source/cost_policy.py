"""Experimental five-way risk/cost/utility policy with empirical calibration.

The action cost table is an explicit assumption. Terminal interventions have no
external effect and no completion in this simulator. See docs/COST_POLICY_PROTOCOL.md.
"""
from dataclasses import asdict
import hashlib
import math
from .controllers import FEATURE_NAMES,features,sigmoid
from .data import canonical
from .schema import Decision as D,Verdict
from .sandbox import execute

DEFAULT_COSTS={'EXECUTE':0.,'CLARIFY':1.,'STAGE':2.,'ESCALATE':3.,'REFUSE':4.}


def validate(a):
    if a.get('schema_version')!='cost-policy-v1' or a.get('features')!=list(FEATURE_NAMES):raise ValueError('incompatible cost policy')
    for key in ('risk_weights','utility_weights'):
        if len(a.get(key,[]))!=len(FEATURE_NAMES) or any(type(w) not in (int,float) or not math.isfinite(w) for w in a[key]):raise ValueError('invalid cost-policy weights')
    costs=a.get('costs',{})
    if set(costs)!=set(DEFAULT_COSTS) or any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in costs.values()):raise ValueError('invalid action costs')
    for key in ('risk_multiplier','utility_multiplier'):
        if type(a.get(key)) not in (int,float) or not math.isfinite(a[key]) or a[key]<0:raise ValueError('invalid multiplier')


def admissible(x):
    if not x.policy_allows or x.resource!=x.proposed_resource or x.amount!=x.requested_amount:return (D.REFUSE,)
    if not x.authorized or x.approval_required:return (D.ESCALATE,D.REFUSE) if x.approval_available else (D.REFUSE,)
    choices=[D.EXECUTE,D.STAGE,D.REFUSE]
    if not x.referent_known or x.uncertainty>.5 or x.evidence_support<.5:choices.append(D.CLARIFY)
    if x.approval_available:choices.append(D.ESCALATE)
    return tuple(choices)


class CostPolicy:
    name='tharun_cost_calibrated'
    threshold=None
    def __init__(self,artifact):
        validate(artifact);self.artifact=artifact
        self.dependency={'method':'exploratory-five-way-cost-policy','parameters':{
            k:artifact[k] for k in ('risk_multiplier','utility_multiplier','alpha','minimum_autonomy','costs')}}

    def decide(self,x):
        vector=features(x)
        risk=sigmoid(sum(w*f for w,f in zip(self.artifact['risk_weights'],vector)))
        utility=sigmoid(sum(w*f for w,f in zip(self.artifact['utility_weights'],vector)))
        options=[]
        for decision in admissible(x):
            r=risk if decision==D.EXECUTE else 0.
            u=utility if decision==D.EXECUTE else 0.
            cost=self.artifact['costs'][decision.value]
            score=cost+self.artifact['risk_multiplier']*r-self.artifact['utility_multiplier']*u
            options.append((score,cost,decision.value,r))
        _,_,selected,selected_risk=min(options)
        return Verdict(D(selected),'minimum_predicted_risk_cost_utility_objective',selected_risk)


def _learn(rows,targets,steps=600):
    weights=[0.]*len(FEATURE_NAMES)
    xs=[features(r.observation) for r in rows]
    for _ in range(steps):
        grad=[0.]*len(weights)
        for x,y in zip(xs,targets):
            error=sigmoid(sum(w*f for w,f in zip(weights,x)))-y
            for i,f in enumerate(x):grad[i]+=error*f
        weights=[w-.2*(g/len(xs)+(.01*w if i else 0)) for i,(w,g) in enumerate(zip(weights,grad))]
    return weights


def fit_cost_policy(train,calibration,alpha=.05,minimum_autonomy=.5):
    if not train or not calibration:raise ValueError('train and calibration required')
    if not 0<=alpha<=1 or not 0<=minimum_autonomy<=1:raise ValueError('constraints must be in [0,1]')
    if any(r.split!='train' for r in train) or any(r.split!='calibration' for r in calibration):raise ValueError('cost fit excludes test/transfer data')
    if {r.family_id for r in train}&{r.family_id for r in calibration}:raise ValueError('cost-policy family leakage')
    outcomes=[execute(r,D.EXECUTE) for r in train]
    base={'schema_version':'cost-policy-v1','features':list(FEATURE_NAMES),
        'risk_weights':_learn(train,[o['severity_loss'] for o in outcomes]),
        'utility_weights':_learn(train,[float(o['completed'] and r.oracle.autonomous_feasible) for r,o in zip(train,outcomes)]),
        'costs':dict(DEFAULT_COSTS),'risk_multiplier':0.,'utility_multiplier':0.,
        'alpha':alpha,'minimum_autonomy':minimum_autonomy,'guarantee':'empirical_only',
        'train_families':sorted({r.family_id for r in train}),'calibration_families':sorted({r.family_id for r in calibration}),
        'train_hash':hashlib.sha256(canonical([asdict(r) for r in train]).encode()).hexdigest(),
        'calibration_hash':hashlib.sha256(canonical([asdict(r) for r in calibration]).encode()).hexdigest(),
        'annotation_status':'synthetic_unreviewed','status':'exploratory'}
    eligible=sum(r.oracle.autonomous_feasible for r in calibration)
    if not eligible:raise ValueError('no autonomously feasible calibration tasks')
    trials=[]
    for lam in (0.,.25,.5,1.,2.,4.,8.,16.,32.,64.,128.):
        for gamma in (0.,1.,2.,4.):
            candidate={**base,'risk_multiplier':lam,'utility_multiplier':gamma};policy=CostPolicy(candidate)
            decisions=[policy.decide(r.observation).decision for r in calibration]
            results=[execute(r,d) for r,d in zip(calibration,decisions)]
            mean_loss=sum(o['severity_loss'] for o in results)/len(results)
            autonomy=sum(o['completed'] and r.oracle.autonomous_feasible for r,o in zip(calibration,results))/eligible
            cost=sum(base['costs'][d.value] for d in decisions)/len(decisions)
            trials.append({'risk_multiplier':lam,'utility_multiplier':gamma,'mean_loss':mean_loss,'useful_autonomy':autonomy,'mean_cost':cost})
    feasible=[t for t in trials if t['mean_loss']<=alpha and t['useful_autonomy']>=minimum_autonomy]
    if not feasible:raise ValueError('no empirically feasible risk/cost policy; reduce no constraints silently')
    selected=min(feasible,key=lambda t:(t['mean_cost'],t['mean_loss'],-t['useful_autonomy'],t['risk_multiplier'],t['utility_multiplier']))
    base.update(risk_multiplier=selected['risk_multiplier'],utility_multiplier=selected['utility_multiplier'],calibration=selected,candidates=trials)
    return base
