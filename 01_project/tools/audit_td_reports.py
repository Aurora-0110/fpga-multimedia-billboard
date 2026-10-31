"""Audit TD numerical checkpoint; NEVER equate it with hardware release.
Usage: python audit_td_reports.py --reports DIR --run-log FILE --output FILE
--require-release deliberately fails while documented macro/SiP/CDC review is open.
"""
from pathlib import Path
import argparse,json,re

def audit(reports,run_log):
    reports=Path(reports); failures=[]; texts={}
    for name in ['sdram_phy.ts','sdram_pr.timing','route.qor','sdram_check.rpt','abnormal_timing_targets.rpt']:
        f=reports/name
        if not f.is_file(): failures.append('missing '+name);texts[name]=''
        else:texts[name]=f.read_text(encoding='utf-8',errors='replace')
    log=Path(run_log).read_text(encoding='utf-8',errors='replace') if Path(run_log).is_file() else ''
    if not log:failures.append('missing run log')
    values={}
    for key in ['SWNS','STNS','HWNS','HTNS']:
        m=re.search(r'\b'+key+r':\s*(-?\d+(?:\.\d+)?)ns',texts['sdram_phy.ts'])
        values[key]=float(m[1]) if m else None
        if not m:failures.append('missing numeric '+key)
        elif (key.endswith('WNS') and float(m[1])<0) or (key.endswith('TNS') and float(m[1])!=0):failures.append('failing '+key)
    cov=re.search(r'STA coverage\s*:\s*([\d.]+)%',texts['sdram_pr.timing'])
    if not cov or float(cov[1])<99:failures.append('missing/low STA coverage')
    for label in ['S','H']:
        m=re.search(r'Num of violated '+label+r'-EP\s*\|\s*(\d+)',texts['route.qor'])
        if not m or int(m[1])!=0:failures.append('missing/nonzero '+label+' endpoint count')
    if 'Confidence          : Routed' not in texts['sdram_pr.timing']:failures.append('no routed timing evidence')
    if not re.search(r'End Stage \d+(?:\.\d+)* \| Routing DRC(?:[;\n]|$)',log):failures.append('route did not complete')
    if re.search(r'\bERROR\b|@@@ TASK_ERROR',log):failures.append('TD error in run log')
    if re.search(r'^End Point:',texts['abnormal_timing_targets.rpt'],re.M):failures.append('abnormal timing targets remain')
    counts={name:int(count) for name,count in re.findall(r'^\d+\. checking (.*?)\((\d+)\) \((?:HIGH|MEDIUM)\)',texts['sdram_check.rpt'],re.M)}
    for name in ['no clock','clock definition','invalid constraint','combinational loops']:
        if counts.get(name)!=0:failures.append('missing/nonzero '+name)
    warnings=[line for line in log.splitlines() if 'WARNING:' in line]
    codes=['TMR-6048','PHY-5014','USR-6135','PHY-7002']
    warning_flags={code:bool(re.search(r'\b'+code+r'\b',log)) for code in codes}
    feedback_ok=not any(warning_flags[c] for c in codes[:3]) and counts.get('pll/clock buffer clock constraints')==0 and bool(texts['sdram_check.rpt'])
    open_review=[]
    if not feedback_ok:open_review.append('PLL feedback checkpoint NOT closed: inspect warning_flags and clock constraint count')
    if warning_flags['PHY-7002']:open_review.append('PHY-7002 hard-macro initial relocation persists; do not force unsupported coordinates')
    open_review += [f"SiP voltage/speed grade and TD internal DQ delay annotations need vendor confirmation; {counts.get('abnormal input delay', 'unknown')} abnormal input delay entries are NOT waived",
                    'dummy/undriven nodes and external LED interface timing need documented review',
                    'No real-device programming, full-address BIST or PVT robustness acceptance']
    return dict(numerical_checkpoint_pass=not failures,failures=failures,slack_ns=values,coverage_percent=float(cov[1]) if cov else None,check_timing_counts=counts,warnings=warnings,warning_flags=warning_flags,pll_feedback_checkpoint_pass=feedback_ok,formal_release_approved=False,new_hardware_acceptance=False,open_review=open_review)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--reports',type=Path,required=True);p.add_argument('--run-log',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--require-release',action='store_true');a=p.parse_args()
    result=audit(a.reports,a.run_log);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if result['numerical_checkpoint_pass'] and not a.require_release else 2)
