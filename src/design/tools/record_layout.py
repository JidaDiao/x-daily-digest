#!/usr/bin/env python3
"""从 blocks/_layout.json 补记 design-used-layouts.json。正常情况 build.py 成功后已自动 append。
用法: python3 tools/record_layout.py 2026-11-04 [--blocks DIR]
"""
import os,sys,json,argparse
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap=argparse.ArgumentParser();ap.add_argument('date');ap.add_argument('--blocks',default='blocks')
A=ap.parse_args()
lp=os.path.join(A.blocks,'_layout.json')
if not os.path.exists(lp):
    sys.exit(f'[record_layout] 缺 {lp}')
L=json.load(open(lp))
used_path='design-used-layouts.json'
data=json.load(open(used_path)) if os.path.exists(used_path) else {'entries':[]}
ents=data.setdefault('entries',[])
entry={'date':A.date,'layout':L.get('layout'),'dims':L.get('dims') or {},'diffs':L.get('diffs') or {},'stance':L.get('stance') or '','note':L.get('why') or L.get('note') or ''}
ents=[e for e in ents if e.get('date')!=A.date]
ents.append(entry); ents.sort(key=lambda e:e.get('date') or '')
data['entries']=ents
open(used_path,'w').write(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print(f'[record_layout] {A.date} → {entry["layout"]} diffs={entry["diffs"]}')
