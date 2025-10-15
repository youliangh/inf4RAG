
import json, time, statistics, threading, requests, os, random

BASE=os.environ.get("BASE","http://127.0.0.1:8000")
URL=f"{BASE}/v1/chat/completions"
MODEL=os.environ.get("MODEL","Qwen/Qwen1.5-MoE-A2.7B-Chat")
N=int(os.environ.get("N","256"))           # total requests
C=int(os.environ.get("C","8"))             # concurrency
IN_LEN=int(os.environ.get("IN_LEN","32"))  # approx prompt length
OUT_LEN=int(os.environ.get("OUT_LEN","512"))

HDR={"Content-Type":"application/json"}
PROMPT=("hello " * IN_LEN).strip()

def one():
    t=time.time()
    r=requests.post(URL, headers=HDR, data=json.dumps({
        "model": MODEL,
        "messages":[{"role":"user","content":PROMPT}],
        "max_tokens": OUT_LEN
    }), timeout=300)
    dt=time.time()-t
    j=r.json()
    u=j.get("usage",{}) or {}
    toks=(u.get("prompt_tokens",0)+u.get("completion_tokens",0))
    return dt, toks, j.get("id","")

runs=[]; lock=threading.Lock()

def worker(k):
    local=[]
    while True:
        with lock:
            if len(runs) >= N: break
            runs.append(None)   # reserve slot
        local.append(one())
    with lock:
        for i,val in enumerate(local):
            # replace placeholders (not perfect but fine for stats)
            for idx,x in enumerate(runs):
                if x is None:
                    runs[idx]=val
                    break

threads=[threading.Thread(target=worker, args=(i,)) for i in range(C)]
t0=time.time()
for th in threads: th.start()
for th in threads: th.join()
t1=time.time()

lat=[x[0] for x in runs if x]
tok=[x[1] for x in runs if x]
tok_total=sum(tok)
elapsed=t1-t0
reqps=len(lat)/elapsed if elapsed>0 else 0
tokps=tok_total/elapsed if elapsed>0 else 0
p50=statistics.median(lat)
p90=statistics.quantiles(lat, n=10)[-1] if len(lat)>=10 else max(lat)
p99=sorted(lat)[int(0.99*len(lat))-1] if len(lat)>=100 else max(lat)

print(f"requests: {len(lat)}  concurrency: {C}")
print(f"latency  mean: {statistics.mean(lat):.3f}s  p50: {p50:.3f}s  p90: {p90:.3f}s  p99: {p99:.3f}s")
print(f"throughput req/s: {reqps:.2f}  tokens/s: {tokps:.1f}  total_tokens: {tok_total}")


