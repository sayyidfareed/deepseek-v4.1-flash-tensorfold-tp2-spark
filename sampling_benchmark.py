import sys,json,time,threading,concurrent.futures,statistics,hashlib,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'upstream/python/tools/dsv41'))
from kit_bench import Client,ORACLE_SET_V1,cmd_ready,cmd_decode
from types import SimpleNamespace
c=Client(os.environ.get('BASE_URL','http://127.0.0.1:8000'),os.environ.get('MODEL','deepseek-v4.1-flash-tp2'),os.environ.get('API_KEY'))
ready=cmd_ready(c,SimpleNamespace(timeout=420)); print(json.dumps({'ready':ready}),flush=True)
fixtures=json.loads((ROOT/'evidence/sampled-requests.json').read_text())['requests']
rows=[]
for parallel in [1,8]:
 for rep in range(3):
  barrier=threading.Barrier(parallel)
  def run(i):
   f=fixtures[i]; barrier.wait()
   b={k:f[k] for k in ['prompt','max_tokens','temperature','top_k','top_p','seed']}
   r=c.stream(b,'/v1/completions'); r['index']=i; r['text_sha256']=hashlib.sha256(r['text'].encode()).hexdigest(); return r
  start=time.perf_counter()
  with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as pool: rr=list(pool.map(run,range(8)))
  elapsed=time.perf_counter()-start
  row={'parallel':parallel,'repeat':rep,'seconds':elapsed,'aggregate_tok_s':sum(r['tokens'] for r in rr)/elapsed,'ttft_median':statistics.median(r['ttft_s'] for r in rr),'responses':rr}
  rows.append(row); print(json.dumps({k:v for k,v in row.items() if k!='responses'}),flush=True)
greedy=cmd_decode(c,SimpleNamespace(set='b',tokens=384,reps=3))
result={'greedy':greedy,'arm':sys.argv[1],'ready':ready,'runs':rows,'note':'SSE /v1/completions with exact chat prompt IDs; three passes including the first cold-prefix pass. Native loopback, seeded temperature 1/top_k20/top_p0.95, max256; eight short distinct prompts.'}
Path('sampling-results-'+sys.argv[1]+'.json').write_text(json.dumps(result,indent=2)+'\n')
