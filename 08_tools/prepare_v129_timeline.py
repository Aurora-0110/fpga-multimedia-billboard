"""Two local exact-text alignments; keep disagreements, no human verification claim."""
from pathlib import Path
import json,re,hashlib,statistics
r=Path(__file__).resolve().parents[1];assert '01_versions'not in r.parts
src=r/'06_test_media/captions_third_user';textpath=src/'TURANDETUOLUO_用户提供完整歌词.txt';lines=textpath.read_text(encoding='utf-8').splitlines()
a,b=[json.loads((r/f'04_evidence/v129_forced_alignment_{m}_attempt1/alignment.json').read_text(encoding='utf-8'))for m in ['turbo','small']]
assert a['complete']and b['complete']and len(lines)==len(a['rows'])==len(b['rows'])==16
source=json.loads((src/'SOURCE.json').read_text(encoding='utf-8'));rows=[];review=[]
for x,y,text in zip(a['rows'],b['rows'],lines):
 assert x['line']==y['line']and x['text']==y['text']==text
 reasons=[];onsets=[max(z['start'],z['words'][0]['end']-.650)for z in [x,y]]
 start=round(statistics.mean(onsets)*1000);end=round(statistics.mean([x['end'],y['end']])*1000)
 if abs(x['start']-y['start'])>.24:reasons.append('model_onset_disagreement')
 if abs(x['end']-y['end'])>.24:reasons.append('model_end_disagreement')
 if any(z['zero_duration_words']for z in [x,y]):reasons.append('zero_duration_word_in_alignment')
 if min(z['mean_probability']for z in [x,y])<.5:reasons.append('weak_model_text_support_not_a_calibrated_confidence')
 if any(onsets[i]>z['start']+.02 for i,z in enumerate([x,y])):reasons.append('leading_word650ms_cap_applied_not_human_QA')
 rows.append(dict(source_line=x['line'],text=text,start_ms=start,end_ms=end,human_timing_verified=False,review_reasons=reasons,raw_turbo=[x['start'],x['end']],raw_small=[y['start'],y['end']]))
for i,q in enumerate(rows):
 if i+1<len(rows)and q['end_ms']>rows[i+1]['start_ms']:
  q['overlap_trim_ms']=q['end_ms']-rows[i+1]['start_ms'];q['end_ms']=rows[i+1]['start_ms'];q['review_reasons'].append('single_line_overlap_end_trim')
 assert 0<q['start_ms']<q['end_ms']<=source['duration_seconds']*1000
 if i:assert q['start_ms']>=rows[i-1]['end_ms']
 assert q['text']==lines[i]
 if q['review_reasons']:review.append(dict(cue=i,text=q['text'],start_ms=q['start_ms'],end_ms=q['end_ms'],reasons=q['review_reasons']))
def stamp(ms):return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
(src/'TURANDETUOLUO_自动对齐待听校.srt').write_text('\n\n'.join(f'{i+1}\n{stamp(q["start_ms"])} --> {stamp(q["end_ms"])}\n{q["text"]}'for i,q in enumerate(rows))+'\n',encoding='utf-8-sig')
rec=dict(version='V129',text_source='Exact16 user-supplied lines, no replacement by ASR',source_sha256=source['audio_expected_sha256'],source_text_sha256=source['user_text_sha256'],source_line_count=16,cue_count=16,full_user_text_covered=True,human_timing_verified=False,alignment_method='Two cached local models cross-attention/DTW; averaged650ms-capped onset and end; explicit overlap trims. Automatic estimate, requires listening/HDMI latency check.',rows=rows,review=review,unsubtitled_sections='Spoken commentary before singing and after lyrics not supplied by user; no invented captions',model_probability_is_not_calibrated_confidence=True)
(src/'TURANDETUOLUO_完整时间轴.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(rec,ensure_ascii=False,indent=2))
