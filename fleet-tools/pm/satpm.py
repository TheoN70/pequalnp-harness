# Exact synthesis of a fan-in-2 circuit (AND/OR, optionally NOT) for K6 perfect matching.
# usage: satpm.py k [not] [seconds]   ; CEGAR: starts on decisive points, adds counterexamples.
import sys, itertools, time
from pysat.solvers import Solver
from pysat.card import CardEnc
M=[(0,9,14),(0,10,13),(0,11,12),(1,6,14),(1,7,13),(1,8,12),(2,5,14),(2,7,11),(2,8,10),(3,5,13),(3,6,11),(3,8,9),(4,5,12),(4,6,10),(4,7,9)]
n=15; masks=[sum(1<<e for e in m) for m in M]
f=lambda x: any(x&m==m for m in masks)
k=int(sys.argv[1]); useNot='not' in sys.argv[2:]
pts=list(masks)+[x for x in range(1<<n) if not f(x) and all(f(x|1<<e) for e in range(n) if not x>>e&1)]
print('decisive',len(pts),flush=True)
nv=[0]
def new(): nv[0]+=1; return nv[0]
W=n+k
s1=[[new() for j in range(n+i)] for i in range(k)]; s2=[[new() for j in range(n+i)] for i in range(k)]
tAND=[new() for i in range(k)]; tNOT=[new() for i in range(k)] if useNot else None
cl=[]
def exactly1(vs):
    cl.extend(CardEnc.equals(vs,1,top_id=nv[0]).clauses); nv[0]=max(nv[0],max(abs(l) for c in cl[-50:] for l in c))
for i in range(k):
    for vs in (s1[i],s2[i]):
        e=CardEnc.equals(vs,1,top_id=nv[0]); cl.extend(e.clauses); nv[0]=max(nv[0],e.nv)
    # s1 index < s2 index (unless NOT gate, where s2 ignored -> force s2=last? keep order anyway)
    for a in range(n+i):
        for b in range(a+1):
            if useNot: cl.append([-s1[i][a],-s2[i][b],tNOT[i]])
            else: cl.append([-s1[i][a],-s2[i][b]])
    if useNot:
        cl.append([-tNOT[i],-tAND[i]])
        for a in range(n+i):
            for b in range(n+i):
                if b!=a: cl.append([-tNOT[i],-s1[i][a],-s2[i][b]])  # NOT: s2==s1
    # every non-output gate used
    if i<k-1: cl.append([s1[g][n+i] for g in range(i+1,k)]+[s2[g][n+i] for g in range(i+1,k)])
if 'sym' in sys.argv:  # S6 on K6 edges: an input-only gate can go first and be mapped to edges {0,1} (adjacent) or {0,9} (disjoint)
    cl.append([s1[0][0]]); cl.append([s2[0][j] for j in ((0,1,9) if useNot else (1,9))])
S=Solver(name='cadical195',bootstrap_with=cl)
def addpt(x):
    v=[(1 if x>>j&1 else -1)*0 for j in range(n)]
    val=[None]*W
    for j in range(n): val[j]=bool(x>>j&1)
    lit=lambda w: val[w]
    gv=[new() for i in range(k)]
    C=[]
    def L(w):  # literal-or-constant for wire w
        return val[w] if w<n else gv[w-n]
    for i in range(k):
        a=new(); b=new(); g=gv[i]
        for (sel,y) in ((s1,a),(s2,b)):
            for j in range(n+i):
                s=sel[i][j]; w=L(j)
                if w is True: C.append([-s,y])
                elif w is False: C.append([-s,-y])
                else: C+= [[-s,-w,y],[-s,w,-y]]
        t=tAND[i]
        if useNot:
            u=tNOT[i]
            C+= [[-u,-a,-g],[-u,a,g]]
            C+= [[u,-t,-g,a],[u,-t,-g,b],[u,-t,g,-a,-b]]
            C+= [[u,t,g,-a],[u,t,g,-b],[u,t,-g,a,b]]
        else:
            C+= [[-t,-g,a],[-t,-g,b],[-t,g,-a,-b]]
            C+= [[t,g,-a],[t,g,-b],[t,-g,a,b]]
    C.append([gv[-1] if f(x) else -gv[-1]])
    for c in C: S.add_clause(c)
for x in pts: addpt(x)
def decode(m):
    ms=set(l for l in m if l>0); G=[]
    for i in range(k):
        a=next(j for j in range(n+i) if s1[i][j] in ms); b=next(j for j in range(n+i) if s2[i][j] in ms)
        op='not' if useNot and tNOT[i] in ms else ('and' if tAND[i] in ms else 'or')
        G.append((op,a,b))
    return G
def ev(G,x):
    v=[x>>j&1 for j in range(n)]
    for op,a,b in G: v.append(1-v[a] if op=='not' else (v[a]&v[b] if op=='and' else v[a]|v[b]))
    return v[-1]
t0=time.time(); it=0
HINT=[]
if 'hint' in sys.argv:  # known 34: vertex 0 to each other vertex, times the K4 matchings
    G=[]; top=[]
    for e in range(5):
        ps=[m[1:] for m in M if m[0]==e]; base=n+len(G)
        G+= [('and',)+ps[0],('and',)+ps[1],('and',)+ps[2],('or',base,base+1),('or',base+2,base+3),('and',e,base+4)]
        top.append(n+len(G)-1)
    acc=top[0]
    for t in top[1:]: G.append(('or',min(acc,t),max(acc,t))); acc=n+len(G)-1
    assert len(G)==k and all(ev(G,x)==f(x) for x in range(1<<n))
    for i,(op,a,b) in enumerate(G): HINT+= [s1[i][a],s2[i][b],tAND[i] if op=='and' else -tAND[i]]
while True:
    r=S.solve(assumptions=HINT); it+=1
    if not r: print('UNSAT k=%d not=%s %.0fs iters=%d'%(k,useNot,time.time()-t0,it)); break
    G=decode(S.get_model())
    bad=[x for x in range(1<<n) if ev(G,x)!=f(x)]
    if not bad:
        print('SAT k=%d %.0fs'%(k,time.time()-t0)); print(G); break
    print('iter',it,'cex',len(bad),flush=True)
    for x in bad[:20]: addpt(x)
