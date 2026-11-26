// Exact circuit size of a Boolean function on 6 inputs by a live-wire search.
// State: the set of wires still to be read (live). A step reads two live wires, adds a gate, and each operand
// either dies or stays. With r steps left a state needs at most r+1 live wires and the target must be a
// function (monotone function in mode 0) of the live wires.
// mode 0: AND, OR.  mode 1: signed (a&b, a|b, a&~b, b&~a), NOT free.  mode 2: AND, OR, NOT (NOT costs a step).
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint64_t u64;
#define MAXL 20
static u64 F; static int MODE, SYM;
static int nT, T[64], nMin, Mn[64];
static u64 nodes, hits, stored;
static inline u64 sw01(u64 t){ return (t & 0x9999999999999999ULL) | ((t & 0x2222222222222222ULL) << 1) | ((t & 0x4444444444444444ULL) >> 1); }
static inline u64 sw12(u64 t){ return (t & 0xC3C3C3C3C3C3C3C3ULL) | ((t & 0x0C0C0C0C0C0C0C0CULL) << 2) | ((t & 0x3030303030303030ULL) >> 2); }
static inline u64 sw02(u64 t){ return (t & 0xA5A5A5A5A5A5A5A5ULL) | ((t & 0x0A0A0A0A0A0A0A0AULL) << 3) | ((t & 0x5050505050505050ULL) >> 3); }
static inline u64 perm(int p, u64 t){
  switch(p){ case 0: return t; case 1: return sw01(t); case 2: return sw12(t); case 3: return sw02(t);
    case 4: return sw01(sw12(t)); default: return sw12(sw01(t)); } }
static void sortw(u64 *a, int n){ for(int i=1;i<n;i++){ u64 v=a[i]; int j=i-1; while(j>=0 && a[j]>v){a[j+1]=a[j]; j--;} a[j+1]=v; } }
static void canon(u64 *L, int n){
  sortw(L,n); if(!SYM) return;
  u64 best[MAXL], cur[MAXL]; memcpy(best,L,n*sizeof(u64));
  for(int p=1;p<6;p++){ for(int i=0;i<n;i++) cur[i]=perm(p,L[i]); sortw(cur,n);
    for(int i=0;i<n;i++){ if(cur[i]<best[i]){ memcpy(best,cur,n*sizeof(u64)); break; } if(cur[i]>best[i]) break; } }
  memcpy(L,best,n*sizeof(u64)); }
static int separated(const u64 *L, int n){
  if(MODE==0){ for(int k=0;k<nMin;k++){ int a=Mn[k]; u64 B=~0ULL; for(int i=0;i<n;i++) if((L[i]>>a)&1) B&=L[i]; if(B & ~F) return 0; } return 1; }
  for(int k=0;k<nT;k++){ int a=T[k]; u64 D=~0ULL; for(int i=0;i<n;i++) D &= ((L[i]>>a)&1) ? L[i] : ~L[i]; if(D & ~F) return 0; }
  return 1; }
// transposition table: 128-bit key -> largest r that failed
typedef struct { u64 k1,k2; } Key;
static Key *tab; static uint8_t *tabr; static u64 TABMASK;
static inline u64 mix(u64 x){ x^=x>>33; x*=0xff51afd7ed558ccdULL; x^=x>>33; x*=0xc4ceb9fe1a85ec53ULL; x^=x>>33; return x; }
static inline Key hkey(const u64 *L, int n){ Key k; k.k1=0x9E3779B97F4A7C15ULL^n; k.k2=0xD1B54A32D192ED03ULL+n;
  for(int i=0;i<n;i++){ k.k1=mix(k.k1^L[i])+0x165667B19E3779F9ULL; k.k2=mix((k.k2+L[i])*0x2545F4914F6CDD1DULL)^(L[i]>>7); }
  if(!k.k1 && !k.k2) k.k1=1; return k; }
static int tt_failed(Key k, int r){ u64 i=k.k1&TABMASK; for(;;){ if(!tab[i].k1 && !tab[i].k2) return 0;
    if(tab[i].k1==k.k1 && tab[i].k2==k.k2) return tabr[i]>=r; i=(i+1)&TABMASK; } }
static void tt_store(Key k, int r){ u64 i=k.k1&TABMASK; for(;;){ if(!tab[i].k1 && !tab[i].k2){ tab[i]=k; tabr[i]=r; stored++;
      if(stored > (TABMASK>>1)+(TABMASK>>2)){ fprintf(stderr,"table full\n"); exit(2);} return; }
    if(tab[i].k1==k.k1 && tab[i].k2==k.k2){ if(tabr[i]<r) tabr[i]=r; return; } i=(i+1)&TABMASK; } }
typedef struct { u64 a,b,c; int op,keep; } Step;
static Step path[64]; static int depth;
static int dfs(const u64 *L, int n, int r){
  nodes++;
  Key k=hkey(L,n); if(tt_failed(k,r)){ hits++; return 0; }
  int nops = MODE==0 ? 2 : (MODE==1 ? 4 : 2);
  for(int i=0;i<n;i++) for(int j=i+1;j<n;j++){ u64 a=L[i], b=L[j];
    for(int op=0;op<nops;op++){ u64 c = op==0 ? (a&b) : op==1 ? (a|b) : op==2 ? (a&~b) : (b&~a);
      if(c==0 || c==~0ULL || c==a || c==b) continue;
      int dup=0; for(int t=0;t<n;t++) if(L[t]==c){dup=1;break;} if(dup) continue;
      for(int keep=0;keep<4;keep++){ int n2=n-2+(keep&1)+((keep>>1)&1)+1;
        path[depth]=(Step){a,b,c,op,keep};
        if(n2==1){ if(c==F){ depth++; return 1; } continue; }
        if(r-1<=0 || n2>r) continue;
        u64 L2[MAXL]; int m=0; for(int t=0;t<n;t++){ if(t==i && !(keep&1)) continue; if(t==j && !(keep&2)) continue; L2[m++]=L[t]; } L2[m++]=c;
        if(!separated(L2,m)) continue;
        canon(L2,m); depth++; if(dfs(L2,m,r-1)) return 1; depth--; } } }
  if(MODE==2) for(int i=0;i<n;i++){ u64 a=L[i], c=~a; int dup=0; for(int t=0;t<n;t++) if(L[t]==c){dup=1;break;} if(dup) continue;
      for(int keep=0;keep<2;keep++){ int n2=n-1+keep+1; path[depth]=(Step){a,0,c,4,keep};
        if(n2==1){ if(c==F){ depth++; return 1; } if(r-1<=0) continue; }
        if(r-1<=0 || n2>r) continue;
        u64 L2[MAXL]; int m=0; for(int t=0;t<n;t++){ if(t==i && !keep) continue; L2[m++]=L[t]; } L2[m++]=c;
        if(!separated(L2,m)) continue;
        canon(L2,m); depth++; if(dfs(L2,m,r-1)) return 1; depth--; } }
  tt_store(k,r); return 0; }
int main(int argc, char **argv){
  if(argc<7){ fprintf(stderr,"usage: live <hex table> <varmask> <mode> <sym> <lo> <hi> [log2 table]\n"); return 1; }
  F=strtoull(argv[1],0,16); int vm=strtol(argv[2],0,0); MODE=atoi(argv[3]); SYM=atoi(argv[4]); int lo=atoi(argv[5]), hi=atoi(argv[6]);
  int lg = argc>7 ? atoi(argv[7]) : 24; TABMASK=(1ULL<<lg)-1; tab=calloc(TABMASK+1,sizeof(Key)); tabr=calloc(TABMASK+1,1);
  static const u64 X[6]={0xAAAAAAAAAAAAAAAAULL,0xCCCCCCCCCCCCCCCCULL,0xF0F0F0F0F0F0F0F0ULL,0xFF00FF00FF00FF00ULL,0xFFFF0000FFFF0000ULL,0xFFFFFFFF00000000ULL};
  for(int a=0;a<64;a++) if((F>>a)&1){ T[nT++]=a; int minimal=1; for(int i=0;i<6;i++) if(((a>>i)&1) && ((F>>(a&~(1<<i)))&1)) minimal=0; if(minimal) Mn[nMin++]=a; }
  if(SYM && (sw01(F)!=F || sw12(F)!=F)){ fprintf(stderr,"target is not symmetric in inputs 0-2\n"); return 1; }
  u64 L[MAXL]; int n=0; for(int i=0;i<6;i++) if((vm>>i)&1) L[n++]=X[i];
  printf("target %016llx true points %d minimal %d inputs %d mode %d sym %d\n",(unsigned long long)F,nT,nMin,n,MODE,SYM);
  if(!separated(L,n)){ printf("inputs do not determine the target\n"); return 1; }
  canon(L,n);
  for(int N=lo;N<=hi;N++){ depth=0; nodes=hits=0; int ok=dfs(L,n,N);
    printf("N=%d %s nodes=%llu tt-hits=%llu stored=%llu\n",N,ok?"FOUND":"none",(unsigned long long)nodes,(unsigned long long)hits,(unsigned long long)stored); fflush(stdout);
    if(ok){ static const char *nm[5]={"and","or","andnot","notand","not"};
      for(int d=0;d<depth;d++) printf("  %s %016llx %016llx -> %016llx keep=%d\n",nm[path[d].op],(unsigned long long)path[d].a,(unsigned long long)path[d].b,(unsigned long long)path[d].c,path[d].keep);
      break; } }
  return 0; }
