"""Standalone HTML/CSV/SVG reports derived only from logged observations."""
from collections import defaultdict
from pathlib import Path
from html import escape
import csv
import json
from .experiment import group_summary
from .metrics import bootstrap_difference


def fmt(value):
    if value is None:return 'n/a'
    if isinstance(value,float):return f'{value:.4f}'
    return str(value)


def generate_report(run_dir,rows,manifest):
    run_dir=Path(run_dir);summaries=group_summary(rows)
    if not summaries:raise ValueError("cannot report an empty run")
    (run_dir/'summary.json').write_text(json.dumps(summaries,indent=2),encoding='utf-8')
    with (run_dir/'summary.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(summaries[0]));writer.writeheader();writer.writerows(summaries)
    columns=[('system','System'),('model','Local model'),('n','Cases'),('families','Families'),('decision_accuracy','Label agreement'),
        ('useful_autonomy','Useful autonomy'),('mean_severity_loss','Severity loss'),('unjustified_refusal_rate','Unjustified refusal'),
        ('duplicate_effect_rate','Duplicate / exposed fault'),('errors','Errors'),('latency_p95_seconds','Latency p95 (s)')]
    columns.append(('declared_intervention_cost_units','Declared cost units'))
    header=''.join(f'<th>{escape(label)}</th>' for key,label in columns)
    body=''.join('<tr>'+''.join(f'<td>{escape(fmt(r.get(key)))}</td>' for key,label in columns)+'</tr>' for r in summaries)
    width,height=720,360;svg=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Observed useful autonomy and severity loss">',
        '<rect width="720" height="360" fill="#f4f8fa"/><path d="M65 25V300H680" fill="none" stroke="#456"/>',
        '<text x="250" y="344" font-family="sans-serif" font-size="14">Useful autonomy (0 to 1)</text>',
        '<text x="65" y="18" font-family="sans-serif" font-size="13">Severity loss (0 to 1); lower is better</text>']
    palette=['#007f83','#b14635','#6974ad','#a06a12','#425569','#0d8359','#bc5b97','#555']
    for i,s in enumerate(summaries):
        if s['useful_autonomy'] is None:continue
        x=65+600*s['useful_autonomy'];y=300-270*s['mean_severity_loss']
        svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="6" fill="{palette[i%len(palette)]}"><title>{escape(s["system"])}; threshold={s["threshold"]}; U={s["useful_autonomy"]:.4f}, R={s["mean_severity_loss"]:.4f}</title></circle>')
    for tick in (0,.25,.5,.75,1):
        svg.append(f'<text x="{65+600*tick}" y="319" font-size="11" font-family="sans-serif">{tick:g}</text>')
        svg.append(f'<text x="30" y="{304-270*tick}" font-size="11" font-family="sans-serif">{tick:g}</text>')
    svg.append('</svg>');chart=''.join(svg);(run_dir/'frontier.svg').write_text(chart,encoding='utf-8')
    paired=[];groups=defaultdict(list)
    for r in rows:groups[(r['system'],r['model'],r.get('threshold'))].append(r)
    target=groups.get(('tharun_calibrated',None,None))
    if target:
        for key,values in groups.items():
            if key==('tharun_calibrated',None,None):continue
            if {(r['task_id'],r['repeat']) for r in values}=={(r['task_id'],r['repeat']) for r in target}:
                paired.append({'comparator':list(key),**bootstrap_difference(target,values,samples=500)})
    (run_dir/'paired_bootstrap.json').write_text(json.dumps(paired,indent=2),encoding='utf-8')
    warning='ENGINEERING PILOT - SYNTHETIC, UNREVIEWED FIXTURES. NOT PUBLICATION EVIDENCE.'
    experiment_description=('This evaluates bounded model-generated actions and feedback in a local generic SQLite effect ledger.'
        if manifest.get('experiment_type')=='synthetic_closed_loop_agent' else 'This evaluates supplied proposals and a generic local SQLite effect ledger.')
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>THARUN local research run</title><style>body{{font-family:system-ui,sans-serif;line-height:1.6;color:#172f3d;max-width:1160px;margin:40px auto;padding:0 24px}}h1{{font-size:36px}}.notice{{background:#fff3d5;border-left:5px solid #a46b00;padding:18px}}table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{text-align:left;padding:10px;border-bottom:1px solid #d9e4e8}}th{{background:#173344;color:white}}.scroll{{overflow:auto}}svg{{max-width:720px;width:100%}}code{{overflow-wrap:anywhere}}a{{color:#007f83}}</style>
<h1>THARUN: local pilot</h1><p class="notice"><strong>{warning}</strong></p>
<p>Run <code>{escape(manifest['run_id'])}</code> · {escape(manifest['status'])} · API spend $0.</p>
<p>{experiment_description} Domain names are scenario metadata, not eight operational integrations. No independent human review, multi-vendor generalization, deployment safety guarantee or superiority conclusion is established.</p>
<div class="scroll"><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></div>
<h2>Observed operating points</h2>{chart}<p>Dots are measured fixture outcomes, not illustrative paper results. Points can overlap. See the table and CSV for identities. Test threshold sweeps are exploratory; only the threshold selected on calibration data is a candidate confirmatory point.</p>
<h2>Reading the numbers</h2><p>Useful autonomy counts verified safe completion on autonomously feasible tasks; refusals score zero. Harm is averaged across all episodes and remains counted after undo. Duplicate rate uses exposed fault opportunities. Missing denominators are n/a. Model errors fail closed and remain separate errors; their decisions never earn label-agreement credit. Cached calls have low retrieval latency: use original server duration in the raw log when comparing inference cost.</p>
<p>Differences are conditional on this synthetic generator. Policy facts make several gates correct by construction. The current controller selects an empirical execution threshold with deterministic interventions; it does not yet solve the full learned five-way minimum-cost policy.</p>
<p>The separate tharun_cost_calibrated candidate minimizes a declared risk/cost/utility objective using calibration-selected multipliers. Declared cost units are assumptions, not measured dollars or operator time. Terminal interventions have zero simulated completion; long-horizon intervention outcomes are not learned. This exploratory candidate has no risk guarantee and does not supersede earlier negative results.</p>
<h2>Artifacts</h2><p><a href="manifest.json">Manifest</a> · <a href="outcomes.jsonl">Hash-chained outcomes</a> · <a href="summary.csv">CSV</a> · <a href="summary.json">Summary JSON</a> · <a href="paired_bootstrap.json">Family bootstrap</a> · <a href="frontier.svg">Chart SVG</a></p>
<p>Audit hashes detect accidental record edits, not hostile rewriting of the entire chain. Synthetic author labels are not external ground truth.</p></html>'''
    (run_dir/'report.html').write_text(html,encoding='utf-8')
    return summaries

