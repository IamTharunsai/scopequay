"""Compare independent CSV annotations; never auto-create a human review."""
import csv
from collections import Counter
from .schema import Decision
from .data import blind_id


def read_annotations(path,task_ids):
    result={};reviewers=set()
    aliases={blind_id(task):task for task in task_ids}
    with open(path,encoding='utf-8',newline='') as f:
        for row in csv.DictReader(f):
            task=aliases.get(row['task_id'],row['task_id'])
            if task not in task_ids or task in result:raise ValueError('unknown or duplicate task in annotation')
            if not row.get('decision','').strip():continue
            if not row.get('reviewer_id','').strip():raise ValueError('reviewer_id required for labeled rows')
            decision=Decision(row['decision'].strip()).value
            result[task]=decision;reviewers.add(row['reviewer_id'].strip())
    if len(reviewers)!=1:raise ValueError('each annotation file must contain exactly one actual reviewer')
    return result,next(iter(reviewers))


def agreement(path_a,path_b,task_ids):
    a,ra=read_annotations(path_a,task_ids);b,rb=read_annotations(path_b,task_ids)
    if ra==rb:raise ValueError('reviewer identities must differ')
    shared=sorted(set(a)&set(b))
    if not shared:raise ValueError('no jointly labeled records')
    n=len(shared);observed=sum(a[k]==b[k] for k in shared)/n
    ac=Counter(a[k] for k in shared);bc=Counter(b[k] for k in shared)
    expected=sum(ac[d.value]*bc[d.value] for d in Decision)/n**2
    return {'reviewers':[ra,rb],'jointly_labeled':n,'coverage_a':len(a),'coverage_b':len(b),
        'agreement':observed,'cohen_kappa':(observed-expected)/(1-expected) if expected<1 else None,
        'disagreements':[{'task_id':k,'a':a[k],'b':b[k]} for k in shared if a[k]!=b[k]],
        'warning':'Agreement is not proof of correctness. Review identities are user-supplied, not authenticated.'}

