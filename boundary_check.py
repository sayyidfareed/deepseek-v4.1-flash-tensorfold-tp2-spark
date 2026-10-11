import json,time,urllib.request,os
from pathlib import Path
root=Path('.');rows=[]
base=os.environ.get('BASE_URL','http://127.0.0.1:8000').rstrip('/')
key=os.environ.get('API_KEY','')
def post(path,data):
 req=urllib.request.Request(base+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json', **({'Authorization':'Bearer '+key} if key else {})})
 with urllib.request.urlopen(req,timeout=180) as r:return json.load(r)
for n,marker in [(72150,'ALPHA'),(72149,'BRAVO'),(72151,'CHARLIE')]:
 text=f'{marker}: This is a padding test. Remember the marker {marker}.\n'+('Repository record: async queue checks cancellation and retries.\n'*15000)+f'\nIgnore padding and reply with only the marker {marker}.'
 ids=post('/tokenize',{'messages':[{'role':'user','content':text}],'reasoning_effort':'none'})['tokens']
 ids=ids[:n-128]+ids[-128:];assert len(ids)==n
 t=time.monotonic();r=post('/v1/completions',{'model':'deepseek-v4.1-flash-tp2','prompt':ids,'max_tokens':32,'temperature':0,'reasoning_effort':'none'})
 answer=r['choices'][0]['text'];passed=r['usage']['prompt_tokens']==n and marker in answer and r['usage']['completion_tokens']>0
 rows.append({'prompt_tokens':n,'seconds':time.monotonic()-t,'usage':r['usage'],'answer':answer,'passed':passed,'tensorfold':r.get('tensorfold')})
 (root/'boundary-results.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows[-1]),flush=True);assert passed
