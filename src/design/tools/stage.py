#!/usr/bin/env python3
"""阶段状态：stage/<date>/state.json
  python3 tools/stage.py <date> next            → 打印下一个未完成阶段（全完成打印 DONE）
  python3 tools/stage.py <date> done <阶段> [备注] → 标记完成（备注写产物路径/候选等）
  python3 tools/stage.py <date> show            → 打印全部状态
阶段顺序：pick → assets → webdemo → build → check → publish → deliver"""
import sys,os,json,time
S=['pick','assets','webdemo','build','check','publish','deliver']
d=sys.argv[1];cmd=sys.argv[2];base=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','stage',d)
os.makedirs(base,exist_ok=True);p=os.path.join(base,'state.json')
st=json.load(open(p)) if os.path.exists(p) else {}
if cmd=='done':
    st[sys.argv[3]]={'at':time.strftime('%Y-%m-%d %H:%M'),'note':' '.join(sys.argv[4:])}
    json.dump(st,open(p,'w'),ensure_ascii=False,indent=1);print('ok',sys.argv[3])
elif cmd=='next': print(next((s for s in S if s not in st),'DONE'))
else: print(json.dumps(st,ensure_ascii=False,indent=1))
