// bfcirc: exhaustive search for a fan-in-2 AND/OR + NOT circuit (every gate counted, pequalnp's FanInTwo model) of at
// most S gates computing a function on given rows: a second method, independent of circsat's SAT encoding, to confirm
// an UNSAT (from Research-L-meta-24473's bf6.c, generalised).
//   bfcirc <n> <S> <table> [rows]          table: pequalnp table (hex 0x.. or decimal), bit r = f on row r, input i =
//                                          bit i of r; rows: comma list (default all 2^n, at most 64 rows);
//                                          a row "r:v" gives its value v explicitly (needed for r >= 64, table ignored there)
//   bfcirc --two-lit <n> <mask> <S>        the two-lit statement: rows 2^i | 2^j (i <= j), value bit n*i + j of mask
//   ... [-k K -m M]                        split: only first gates with index % M == K (run M pieces in parallel)
// Prints the circuit (gate g makes wire n + g) and FOUND, or NONE: no circuit of <= S gates.
// Prunings, each sound for a circuit of minimal size: no gate equals an existing wire or a constant on the rows;
// consecutive gates not reading each other come in increasing (a, b, op) order; unread gate wires <= remaining + 1.
// ponytail: rows packed in one uint64 (<= 64 rows), wires <= 64; plain DFS, split with -k/-m across cores.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

static int N, S, K = -1, MOD = 1, NR, firstcnt;
static uint64_t FULL, T, w[64];
static int ta[64], tb[64], to_[64], used[64];
static long nodes;
static int found = -1;  // number of gates of the circuit found

static int has(int n, uint64_t v) {
  if (v == 0 || v == FULL) return 1;
  for (int i = 0; i < n; i++) if (w[i] == v) return 1;
  return 0;
}
static int gt(int a, int b, int o, int g) {
  if (a != ta[g]) return a > ta[g];
  if (b != tb[g]) return b > tb[g];
  return o > to_[g];
}
static int go(int n, int g) {
  if (g > 0 && w[n - 1] == T) { found = g; return 1; }
  if (g == S) return 0;
  int dang = 0;
  for (int i = N; i < n; i++) if (!used[i]) dang++;
  if (dang > S - g + 1) return 0;
  nodes++;
  for (int a = 0; a < n; a++) for (int b = a; b < n; b++) for (int o = 0; o < 2; o++) {
    if (b == a && o == 1) continue;  // (a,a,0) = NOT a; a < b: AND (o=0) or OR (o=1)
    uint64_t v = b == a ? ~w[a] & FULL : o ? w[a] | w[b] : w[a] & w[b];
    int op = b == a ? 0 : o + 1;
    if (g > 0 && a != n - 1 && b != n - 1 && !gt(a, b, op, g - 1)) continue;
    if (has(n, v)) continue;
    if (g == 0) { int c = firstcnt++; if (K >= 0 && c % MOD != K) continue; }
    ta[g] = a; tb[g] = b; to_[g] = op; w[n] = v; used[n] = 0;
    int ua = used[a], ub = used[b]; used[a] = used[b] = 1;
    int r = go(n + 1, g + 1);
    used[a] = ua; used[b] = ub;
    if (r) return 1;
  }
  return 0;
}
static void addrow(uint64_t row, int val) {
  if (NR == 64) { fprintf(stderr, "more than 64 rows\n"); exit(2); }
  for (int k = 0; k < N; k++) if (row >> k & 1) w[k] |= 1ull << NR;
  if (val) T |= 1ull << NR;
  NR++;
}
int main(int argc, char **argv) {
  for (int i = 1; i + 1 < argc; i++)
    if (!strcmp(argv[i], "-k")) { K = atoi(argv[i + 1]); argv[i] = argv[i + 1] = ""; }
    else if (!strcmp(argv[i], "-m")) { MOD = atoi(argv[i + 1]); argv[i] = argv[i + 1] = ""; }
  char *p[8]; int np = 0;
  for (int i = 1; i < argc && np < 8; i++) if (argv[i][0]) p[np++] = argv[i];
  if (np == 4 && !strcmp(p[0], "--two-lit")) {
    N = atoi(p[1]); unsigned long long mask = strtoull(p[2], 0, 0); S = atoi(p[3]);
    for (int i = 0; i < N; i++) for (int j = i; j < N; j++) addrow((1ull << i) | (1ull << j), mask >> (N * i + j) & 1);
  } else if (np == 3 || np == 4) {
    N = atoi(p[0]); S = atoi(p[1]); unsigned long long tab = strtoull(p[2], 0, 0);
    if (np == 4) { for (char *s = strtok(p[3], ","); s; s = strtok(0, ",")) { char *c = strchr(s, ':'); long r = atol(s);
      if (!c && r >= 64) { fprintf(stderr, "row %ld >= 64: give its value as %ld:0 or %ld:1\n", r, r, r); return 2; }
      addrow(r, c ? atoi(c + 1) & 1 : tab >> r & 1); } }
    else for (long r = 0; r < (1L << N); r++) addrow(r, tab >> r & 1);
  } else {
    fprintf(stderr, "usage: bfcirc <n> <S> <table> [rows] | bfcirc --two-lit <n> <mask> <S>  [-k K -m M]\n"); return 2;
  }
  if (N < 1 || N + S > 64) { fprintf(stderr, "need 1 <= n and n + S <= 64\n"); return 2; }
  FULL = NR == 64 ? ~0ull : (1ull << NR) - 1;
  for (int i = 0; i < N; i++) if (w[i] == T) { printf("S=%d: output is input %d, 0 gates FOUND nodes=0\n", S, i); return 0; }
  int ok = go(N, 0);
  for (int g = 0; ok && g < found; g++)
    if (to_[g]) printf("gate %d = wire %d: %s(%d,%d)\n", g, N + g, to_[g] == 1 ? "AND" : "OR", ta[g], tb[g]);
    else printf("gate %d = wire %d: NOT(%d)\n", g, N + g, ta[g]);
  printf("S=%d n=%d rows=%d K=%d/%d %s nodes=%ld\n", S, N, NR, K, MOD, ok ? "FOUND" : "NONE", nodes);
  return 0;
}
