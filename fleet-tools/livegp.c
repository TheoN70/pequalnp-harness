// Parallel version of liveg.c (OpenMP, shared transposition table): exact AND/OR size of a graph (edge) function,
// or a signed lower bound (two-input gates, NOT free), by the live-wire search on a universe of at most 64 points.
// universe 1: edges + maximal independent sets (exact for AND/OR).
// universe 2: edges + all independent sets of size >= 2 + the all-ones point (stronger for the signed search).
// In signed mode "none" is a valid lower bound on any universe; "FOUND" must be re-checked on all inputs.
// usage: livegp <n> <edges> <mode 0|1> <sym 0|1> <universe 1|2> <N from> <N to> <log2 table> [frontier depth=3]
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>
typedef uint64_t u64;
#define MAXL 28
static u64 F, ALL; static int MODE, SYM, NV, NPT, NE, NTRUE;
static int ea[128], eb[128]; static int pts[64]; static int trueIdx[64];
static int nAut; static uint8_t autp[64][64];
static volatile int found;
static inline u64 permw(int k, u64 w){ u64 r=0; while(w){ int j=__builtin_ctzll(w); w&=w-1; r|=1ULL<<autp[k][j]; } return r; }
static void sortw(u64 *a, int n){ for(int i=1;i<n;i++){ u64 v=a[i]; int j=i-1; while(j>=0 && a[j]>v){a[j+1]=a[j]; j--;} a[j+1]=v; } }
static void canon(u64 *L, int n){
  sortw(L,n); if(!SYM) return;
  u64 best[MAXL], cur[MAXL]; memcpy(best,L,n*sizeof(u64));
  for(int p=0;p<nAut;p++){ for(int i=0;i<n;i++) cur[i]=permw(p,L[i]); sortw(cur,n);
    for(int i=0;i<n;i++){ if(cur[i]<best[i]){ memcpy(best,cur,n*sizeof(u64)); break; } if(cur[i]>best[i]) break; } }
  memcpy(L,best,n*sizeof(u64)); }
static int separated(const u64 *L, int n){
  if(MODE==0){ for(int k=0;k<NTRUE;k++){ int a=trueIdx[k]; u64 B=ALL; for(int i=0;i<n;i++) if((L[i]>>a)&1) B&=L[i]; if(B & ~F) return 0; } return 1; }
  for(int k=0;k<NTRUE;k++){ int a=trueIdx[k]; u64 D=ALL; for(int i=0;i<n;i++) D &= ((L[i]>>a)&1) ? L[i] : ~L[i]; if(D & ~F & ALL) return 0; }
  return 1; }
typedef struct { u64 k1,k2; } Key;
static Key *tab; static uint8_t *tabr; static u64 TABMASK; static u64 storedTotal;
static inline u64 mix(u64 x){ x^=x>>33; x*=0xff51afd7ed558ccdULL; x^=x>>33; x*=0xc4ceb9fe1a85ec53ULL; x^=x>>33; return x; }
static inline Key hkey(const u64 *L, int n){ Key k; k.k1=0x9E3779B97F4A7C15ULL^n; k.k2=0xD1B54A32D192ED03ULL+n;
  for(int i=0;i<n;i++){ k.k1=mix(k.k1^L[i])+0x165667B19E3779F9ULL; k.k2=mix((k.k2+L[i])*0x2545F4914F6CDD1DULL)^(L[i]>>7); }
  if(!k.k1 && !k.k2) k.k1=1; return k; }
static inline int tt_failed(Key k, int r){ u64 i=k.k1&TABMASK; for(;;){ u64 a=tab[i].k1, b=tab[i].k2; if(!a && !b) return 0;
    if(a==k.k1 && b==k.k2) return tabr[i]>=r; i=(i+1)&TABMASK; } }
static __thread u64 nodes, hits, storedLocal;
static inline void tt_store(Key k, int r){ u64 i=k.k1&TABMASK; for(;;){ u64 a=tab[i].k1, b=tab[i].k2;
    if(!a && !b){ tab[i].k1=k.k1; tab[i].k2=k.k2; tabr[i]=r; storedLocal++; return; }
    if(a==k.k1 && b==k.k2){ if(tabr[i]<r) tabr[i]=r; return; } i=(i+1)&TABMASK; } }
static int dfs(const u64 *L, int n, int r){
  if(found) return 0;
  nodes++;
  Key k=hkey(L,n); if(tt_failed(k,r)){ hits++; return 0; }
  int nops = MODE==0 ? 2 : 4;
  for(int i=0;i<n;i++) for(int j=i+1;j<n;j++){ u64 a=L[i], b=L[j];
    for(int op=0;op<nops;op++){ u64 c = (op==0 ? (a&b) : op==1 ? (a|b) : op==2 ? (a&~b) : (b&~a)) & ALL;
      if(c==0 || c==ALL || c==a || c==b) continue;
      int dup=0; for(int t=0;t<n;t++) if(L[t]==c){dup=1;break;} if(dup) continue;
      for(int keep=0;keep<4;keep++){ int n2=n-2+(keep&1)+((keep>>1)&1)+1;
        if(n2==1){ if(c==F){ found=1; return 1; } continue; }
        if(r-1<=0 || n2>r) continue;
        u64 L2[MAXL]; int m=0; for(int t=0;t<n;t++){ if(t==i && !(keep&1)) continue; if(t==j && !(keep&2)) continue; L2[m++]=L[t]; } L2[m++]=c;
        if(!separated(L2,m)) continue;
        canon(L2,m); if(dfs(L2,m,r-1)) return 1; } } }
  if(found) return 0;
  tt_store(k,r); return 0; }
// frontier: all distinct canonical states after d steps
typedef struct { u64 w[MAXL]; int n; } State;
static State *fr; static long nfr, capfr;
static int cmpState(const void *x, const void *y){ const State *a=x, *b=y; if(a->n!=b->n) return a->n-b->n; return memcmp(a->w,b->w,a->n*sizeof(u64)); }
static void expand(const u64 *L, int n, int r, int d){
  if(d==0){ if(nfr==capfr){ capfr=capfr?capfr*2:1024; fr=realloc(fr,capfr*sizeof(State)); } memcpy(fr[nfr].w,L,n*sizeof(u64)); fr[nfr].n=n; nfr++; return; }
  int nops = MODE==0 ? 2 : 4;
  for(int i=0;i<n;i++) for(int j=i+1;j<n;j++){ u64 a=L[i], b=L[j];
    for(int op=0;op<nops;op++){ u64 c = (op==0 ? (a&b) : op==1 ? (a|b) : op==2 ? (a&~b) : (b&~a)) & ALL;
      if(c==0 || c==ALL || c==a || c==b) continue;
      int dup=0; for(int t=0;t<n;t++) if(L[t]==c){dup=1;break;} if(dup) continue;
      for(int keep=0;keep<4;keep++){ int n2=n-2+(keep&1)+((keep>>1)&1)+1;
        if(n2==1){ if(c==F) found=1; continue; }
        if(r-1<=0 || n2>r) continue;
        u64 L2[MAXL]; int m=0; for(int t=0;t<n;t++){ if(t==i && !(keep&1)) continue; if(t==j && !(keep&2)) continue; L2[m++]=L[t]; } L2[m++]=c;
        if(!separated(L2,m)) continue;
        canon(L2,m); expand(L2,m,r-1,d-1); } } } }
int main(int argc, char **argv){
  if(argc<9){ fprintf(stderr,"usage: livegp <n> <edges> <mode> <sym> <universe> <N from> <N to> <log2 table> [frontier depth]\n"); return 1; }
  NV=atoi(argv[1]); { char *s=strdup(argv[2]); for(char *t=strtok(s,","); t; t=strtok(0,",")){ sscanf(t,"%d-%d",&ea[NE],&eb[NE]); NE++; } }
  MODE=atoi(argv[3]); SYM=atoi(argv[4]); int UNI=atoi(argv[5]); int lo=atoi(argv[6]), hi=atoi(argv[7]);
  int lg=atoi(argv[8]); int FD = argc>9 ? atoi(argv[9]) : 3;
  TABMASK=(1ULL<<lg)-1; tab=calloc(TABMASK+1,sizeof(Key)); tabr=calloc(TABMASK+1,1);
  int adj[16]={0}; for(int e=0;e<NE;e++){ adj[ea[e]]|=1<<eb[e]; adj[eb[e]]|=1<<ea[e]; }
  for(int e=0;e<NE;e++){ trueIdx[NTRUE++]=NPT; pts[NPT++]=(1<<ea[e])|(1<<eb[e]); }
  F=(1ULL<<NE)-1;
  for(int m=0;m<(1<<NV);m++){ int ok=1; for(int i=0;i<NV && ok;i++) if(((m>>i)&1) && (adj[i]&m)) ok=0; if(!ok) continue;
    int mx=1; for(int i=0;i<NV && mx;i++) if(!((m>>i)&1) && !(adj[i]&m)) mx=0;
    int take = UNI==1 ? mx : (__builtin_popcount(m)>=2);
    if(take){ if(NPT>=64){ fprintf(stderr,"universe too large\n"); return 1; } pts[NPT++]=m; } }
  if(UNI==2 && NPT<64){ F|=1ULL<<NPT; trueIdx[NTRUE++]=NPT; pts[NPT++]=(1<<NV)-1; }
  ALL = NPT==64 ? ~0ULL : ((1ULL<<NPT)-1);
  u64 X[16]; for(int i=0;i<NV;i++){ X[i]=0; for(int j=0;j<NPT;j++) if((pts[j]>>i)&1) X[i]|=1ULL<<j; }
  if(SYM){ int p[16]; for(int i=0;i<NV;i++) p[i]=i;
    for(;;){ int ok=1, id=1; for(int i=0;i<NV;i++) if(p[i]!=i) id=0;
      for(int e=0;e<NE && ok;e++) if(!((adj[p[ea[e]]]>>p[eb[e]])&1)) ok=0;
      if(ok && !id && nAut<64){ for(int j=0;j<NPT;j++){ int m=0; for(int i=0;i<NV;i++) if((pts[j]>>i)&1) m|=1<<p[i]; int q=-1; for(int t=0;t<NPT;t++) if(pts[t]==m) q=t; autp[nAut][j]=q; } nAut++; }
      int i=NV-2; while(i>=0 && p[i]>p[i+1]) i--; if(i<0) break; int j=NV-1; while(p[j]<p[i]) j--; int t=p[i]; p[i]=p[j]; p[j]=t;
      for(int a=i+1,b=NV-1;a<b;a++,b--){ t=p[a]; p[a]=p[b]; p[b]=t; } } }
  u64 L[MAXL]; int n=0; for(int i=0;i<NV;i++) if(adj[i]) L[n++]=X[i];
  printf("vertices %d edges %d universe %d points (%d true), automorphisms used %d, mode %d, threads %d\n",NV,NE,NPT,NTRUE,nAut,MODE,omp_get_max_threads()); fflush(stdout);
  canon(L,n);
  for(int N=lo;N<=hi;N++){ found=0; nfr=0; double t0=omp_get_wtime();
    int d = FD < N-1 ? FD : (N>1?N-1:0);
    expand(L,n,N,d);
    if(!found){ qsort(fr,nfr,sizeof(State),cmpState); long u=0; for(long i=0;i<nfr;i++) if(i==0 || cmpState(&fr[i],&fr[u-1])) fr[u++]=fr[i]; nfr=u; }
    u64 tn=0, th=0, ts=0;
    if(!found){
      #pragma omp parallel for schedule(dynamic,1) reduction(+:tn,th,ts)
      for(long i=0;i<nfr;i++){ nodes=hits=storedLocal=0; if(!found) dfs(fr[i].w,fr[i].n,N-d); tn+=nodes; th+=hits; ts+=storedLocal; }
    }
    storedTotal+=ts;
    printf("N=%d %s frontier=%ld nodes=%llu tt-hits=%llu stored=%llu (%.0f%% of table) %.1fs\n",N,found?"FOUND":"none",nfr,(unsigned long long)tn,(unsigned long long)th,(unsigned long long)storedTotal,100.0*storedTotal/(TABMASK+1),omp_get_wtime()-t0); fflush(stdout);
    if(found) break;
    if(storedTotal > (TABMASK>>1)+(TABMASK>>2)){ printf("table nearly full, stopping\n"); break; } }
  return 0; }
