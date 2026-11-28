# three_out_gen6.py <id e.g. L-meta-51306> t1 t2 t3 > out.lean  (Normal2's generator, open-goat/pequalnp-proofs#54937)
# "exceed 6 gates at a two-NOT limit" on 5 input bits: template templates/three_out_50195.lean with the search_false split
# recomputed: one decide per first gate (always a NOT), the heaviest first branch split again on its second gate. ~3 min, 6G.
import sys, re, os
uid, tg = sys.argv[1], [int(a) for a in sys.argv[2:5]]
here = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(here, 'templates', 'three_out_50195.lean')).read()
def setOf(l):
    r = 0
    for v in l: r |= 1 << v
    return r
vals = lambda m: [v for v in range(64) if m >> v & 1]
binm = lambda m: setOf([63] + [x for a in vals(m) for b in vals(m) for x in (a & b, a | b)])
negm = lambda m: setOf([63 ^ a for a in vals(m)])
cnt = [0]
def search(l, m, n):
    cnt[0] += 1
    miss = sum(1 for c in tg if not m >> c & 1)
    if l == 0: return miss <= 0
    if miss > l: return False
    if search(l - 1, m, n): return True
    b, ng = binm(m), negm(m)
    for v in range(64):
        if m >> v & 1: continue
        if b >> v & 1 and search(l - 1, m | 1 << v, n): return True
        if n > 0 and ng >> v & 1 and search(l - 1, m | 1 << v, n - 1): return True
    return False
m0 = setOf([62, 60, 56, 48, 32, 0, 63])
assert not search(6, m0, 2), 'unit is false'
assert not [v for v in range(64) if not m0 >> v & 1 and binm(m0) >> v & 1]
firsts = [v for v in range(64) if not m0 >> v & 1 and negm(m0) >> v & 1]
assert firsts == [1, 3, 7, 15, 31]
sizes = {}
for v in firsts:
    cnt[0] = 0; search(5, m0 | 1 << v, 1); sizes[v] = cnt[0]
heavy = max(sizes, key=sizes.get)
m1 = m0 | 1 << heavy
nb = [v for v in range(64) if not m1 >> v & 1 and binm(m1) >> v & 1]
nn = [v for v in range(64) if not m1 >> v & 1 and negm(m1) >> v & 1]
sub = {}
for v in nb: cnt[0] = 0; search(4, m1 | 1 << v, 1); sub['b%d' % v] = cnt[0]
for v in nn: cnt[0] = 0; search(4, m1 | 1 << v, 0); sub['n%d' % v] = cnt[0]
print('-- sizes', sizes, 'heavy', heavy, 'sub', sub, file=sys.stderr)
T = '[%d, %d, %d]' % tuple(tg); M = '(m0 ||| 1 <<< %d)' % heavy
# cut the old split block (from t_skip to the end of s_n7's proof) and rebuild it
i = src.index('theorem t_skip'); j = src.index('theorem s_n15')
k = src.index('theorem m0_bin')
firstlines = ['theorem s_n%d : search %s 5 (m0 ||| 1 <<< %d) 1 = false := by decide +kernel' % (v, T, v) for v in firsts if v != heavy]
blk = ['theorem t_skip : search %s 4 %s 1 = false := by decide +kernel' % (T, M)]
blk += ['theorem t_b%d : search %s 4 (%s ||| 1 <<< %d) 1 = false := by decide +kernel' % (v, T, M, v) for v in nb]
blk += ['theorem t_n%d : search %s 4 (%s ||| 1 <<< %d) 0 = false := by decide +kernel' % (v, T, M, v) for v in nn]
alt = lambda vs: ' ∨ '.join('v = %d' % v for v in vs)
pat = lambda vs: ' | '.join(['rfl'] * len(vs))
blk.append('''
theorem m1_bin : ∀ v, v < 64 → %(M)s.testBit v = false → (bin %(M)s).testBit v = true →
    %(ab)s := by
  decide +kernel

theorem m1_neg : ∀ v, v < 64 → %(M)s.testBit v = false → (neg %(M)s).testBit v = true →
    %(an)s := by
  decide +kernel

theorem s_n%(h)d : search %(T)s 5 %(M)s 1 = false := by
  refine search_step _ 4 %(M)s 1 t_skip ?_ ?_
  · intro v hv hm hb
    rcases m1_bin v hv hm hb with %(pb)s
%(eb)s
  · intro v hv hm _ hn
    rcases m1_neg v hv hm hn with %(pn)s
%(en)s
''' % dict(M=M, T=T, h=heavy, ab=alt(nb), an=alt(nn), pb=pat(nb), pn=pat(nn),
           eb='\n'.join('    · exact t_b%d' % v for v in nb), en='\n'.join('    · exact t_n%d' % v for v in nn)))
# old region between t_skip and m0_bin holds: t_* lemmas, m1 facts, s_n7, s_n15, s_n31; replace wholesale
pre = src[:src.index('theorem s_n1 :')]
mid = '\n'.join(firstlines) + '\n' + '\n'.join(blk) + '\n'
post = src[k:]
out = pre + mid + post
out = out.replace('L_meta_50195', uid.replace('-', '_')).replace('[4, 38, 53]', T)
for a, b in zip((4, 38, 53), tg):
    out = out.replace('(%d : Nat).testBit' % a, '(%d : Nat).testBit' % b)
sys.stdout.write(out)
