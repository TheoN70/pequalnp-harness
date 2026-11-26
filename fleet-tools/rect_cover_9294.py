import sys
from pysat.card import CardEnc,EncType
from pysat.solvers import Cadical153
R=[126,413,683,839,483,725,825,822,730,492]; n=10
rects=set()
for S in range(1,1<<n):
    c=(1<<n)-1
    for i in range(n):
        if S>>i&1: c&=R[i]
    if c: rects.add((sum(1<<i for i in range(n) if R[i]&c==c),c))
rects=sorted(rects); m=len(rects)
cl=[[t+1 for t,(r,c) in enumerate(rects) if r>>i&1 and c>>j&1] for i in range(n) for j in range(n) if R[i]>>j&1]
K=int(sys.argv[1])
card=CardEnc.atmost(list(range(1,m+1)),bound=K,top_id=m,encoding=EncType.seqcounter)
s=Cadical153(bootstrap_with=cl+card.clauses)
if s.solve():
    md=set(x for x in s.get_model() if 0<x<=m)
    for t in sorted(md): r,c=rects[t-1]; print([i for i in range(n) if r>>i&1],[j for j in range(n) if c>>j&1])
else: print("UNSAT",K,"maximal rects",m)
