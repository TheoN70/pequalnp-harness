import sys
from functools import lru_cache
sys.setrecursionlimit(100000)
P,H=int(sys.argv[1]),int(sys.argv[2])
N=P*H
DEAD=None
def close(s):
    s=list(s)
    while True:
        ch=False
        for h in range(H):
            col=[s[p*H+h] for p in range(P)]
            if col.count(2)>1: return DEAD
            if 2 in col:
                for p in range(P):
                    if s[p*H+h]==0: s[p*H+h]=1; ch=True
        for p in range(P):
            r=s[p*H:(p+1)*H]
            if 2 in r: continue
            z=[h for h in range(H) if r[h]==0]
            if not z: return DEAD
            if len(z)==1: s[p*H+z[0]]=2; ch=True
        if not ch: return canon(s)
def canon(s):
    M=[list(s[p*H:(p+1)*H]) for p in range(P)]
    for _ in range(3):
        M.sort(); C=sorted(zip(*M)); M=[list(r) for r in zip(*C)]
    return tuple(x for r in M for x in r)
def st(s,v,b):
    t=list(s);t[v]=b;return close(t)
@lru_cache(None)
def M(t):
    if t is DEAD: return -1
    m=val(t)
    for u in range(N):
        if t[u]==0:
            for b in (1,2): m=max(m,M(st(t,u,b)))
    return m
@lru_cache(None)
def val(s):
    best=10**9
    for v in range(N):
        if s[v]==0:
            best=min(best,1+max(M(st(s,v,1)),M(st(s,v,2))))
            if best==0: break
    return 0 if best==10**9 else best
print(P,H,val(close((0,)*N)),val.cache_info().currsize,flush=True)
