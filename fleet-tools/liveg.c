// Exact AND/OR circuit size of a graph (edge) function on up to 16 vertices, by the live-wire search of live.c
// on a reduced universe: the edges (true points) and the maximal independent sets (false points). A monotone
// circuit computes the edge function exactly when it is right on these points, so the search is exact for AND/OR.
// mode 1 (signed, NOT free) on this universe is only a LOWER bound (a circuit it finds may be wrong elsewhere).
// usage: liveg <n> <edges 0-4,1-5,...> <mode 0|1> <sym 0|1> <N from> <N to> [log2 table]
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint64_t u64;
#define MAXL 28
static u64 F, ALL; static int MODE, SYM, NV, NPT, NE;
static int ea[128], eb[128]; static int pts[64];
static u64 nodes, hits, stored;
static int nAut; static uint8_t autp[64][64];   // point permutations of the non-trivial automorphisms
static inline u64 permw(int k, u64 w){ u64 r=0; while(w){ int j=__builtin_ctzll(w); w&=w-1; r|=1ULL<<autp[k][j]; } return r; }
static void sortw(u64 *a, int n){ for(int i=1;i<n;i++){ u64 v=a[i]; int j=i-1; while(j>=0 && a[j]>v){a[j+1]=a[j]; j--;} a[j+1]=v; } }
static void canon(u64 *L, int n){
  sortw(L,n); if(!SYM) return;
  u64 best[MAXL], cur[MAXL]; memcpy(best,L,n*sizeof(u64));
  for(int p=0;p<nAut;p++){ for(int i=0;i<n;i++) cur[i]=permw(p,L[i]); sortw(cur,n);
    for(int i=0;i<n;i++){ if(cur[i]<best[i]){ memcpy(best,cur,n*sizeof(u64)); break; } if(cur[i]>best[i]) break; } }
  memcpy(L,best,n*sizeof(u64)); }
static int separated(const u64 *L, int n){
  if(MODE==0){ for(int a=0;a<NE;a++){ u64 B=ALL; for(int i=0;i<n;i++) if((L[i]>>a)&1) B&=L[i]; if(B & ~F) return 0; } return 1; }
  for(int a=0;a<NE;a++){ u64 D=ALL; for(int i=0;i<n;i++) D &= ((L[i]>>a)&1) ? L[i] : ~L[i]; if(D & ~F & ALL) return 0; }
  return 1; }
typedef struct { u64 k1,k2; } Key;
static Key *tab; static uint8_t *tabr; static u64 TABMASK;
static inline u64 mix(u64 x){ x^=x>>33; x*=0xff51afd7ed558ccdULL; x^=x>>33; x*=0xc4ceb9fe1a85ec53ULL; x^=x>>33; return x; }
static inline Key hkey(const u64 *L, int n){ Key k; k.k1=0x9E3779B97F4A7C15ULL^n; k.k2=0xD1B54A32D192ED03ULL+n;
  for(int i=0;i<n;i++){ k.k1=mix(k.k1^L[i])+0x165667B19E3779F9ULL; k.k2=mix((k.k2+L[i])*0x2545F4914F6CDD1DULL)^(L[i]>>7); }
  if(!k.k1 && !k.k2) k.k1=1; return k; }
static int tt_failed(Key k, int r){ u64 i=k.k1&TABMASK; for(;;){ if(!tab[i].k1 && !tab[i].k2) return 0;
    if(tab[i].k1==k.k1 && tab[i].k2==k.k2) return tabr[i]>=r; i=(i+1)&TABMASK; } }
static void tt_store(Key k, int r){ u64 i=k.k1&TABMASK; for(;;){ if(!tab[i].k1 && !tab[i].k2){ tab[i]=k; tabr[i]=r; stored++;
      if(stored > (TABMASK>>1)+(TABMASK>>2)){ printf("table full\n"); fflush(stdout); exit(2);} return; }
    if(tab[i].k1==k.k1 && tab[i].k2==k.k2){ if(tabr[i]<r) tabr[i]=r; return; } i=(i+1)&TABMASK; } }
typedef struct { u64 a,b,c; int op,keep; } Step;
static Step path[64]; static int depth;
static int dfs(const u64 *L, int n, int r){
  nodes++;
  Key k=hkey(L,n); if(tt_failed(k,r)){ hits++; return 0; }
  int nops = MODE==0 ? 2 : 4;
  for(int i=0;i<n;i++) for(int j=i+1;j<n;j++){ u64 a=L[i], b=L[j];
    for(int op=0;op<nops;op++){ u64 c = (op==0 ? (a&b) : op==1 ? (a|b) : op==2 ? (a&~b) : (b&~a)) & ALL;
      if(c==0 || c==ALL || c==a || c==b) continue;
      int dup=0; for(int t=0;t<n;t++) if(L[t]==c){dup=1;break;} if(dup) continue;
      for(int keep=0;keep<4;keep++){ int n2=n-2+(keep&1)+((keep>>1)&1)+1;
        path[depth]=(Step){a,b,c,op,keep};
        if(n2==1){ if(c==F){ depth++; return 1; } continue; }
        if(r-1<=0 || n2>r) continue;
        u64 L2[MAXL]; int m=0; for(int t=0;t<n;t++){ if(t==i && !(keep&1)) continue; if(t==j && !(keep&2)) continue; L2[m++]=L[t]; } L2[m++]=c;
        if(!separated(L2,m)) continue;
        canon(L2,m); depth++; if(dfs(L2,m,r-1)) return 1; depth--; } } }
  tt_store(k,r); return 0; }
int main(int argc, char **argv){
  if(argc<7){ fprintf(stderr,"usage: liveg <n> <edges> <mode> <sym> <N from> <N to> [log2 table]\n"); return 1; }
  NV=atoi(argv[1]); { char *s=strdup(argv[2]); for(char *t=strtok(s,","); t; t=strtok(0,",")){ sscanf(t,"%d-%d",&ea[NE],&eb[NE]); NE++; } }
  MODE=atoi(argv[3]); SYM=atoi(argv[4]); int lo=atoi(argv[5]), hi=atoi(argv[6]);
  int lg = argc>7 ? atoi(argv[7]) : 24; TABMASK=(1ULL<<lg)-1; tab=calloc(TABMASK+1,sizeof(Key)); tabr=calloc(TABMASK+1,1);
  int adj[16]={0}; for(int e=0;e<NE;e++){ adj[ea[e]]|=1<<eb[e]; adj[eb[e]]|=1<<ea[e]; }
  for(int e=0;e<NE;e++) pts[NPT++]=(1<<ea[e])|(1<<eb[e]);
  for(int m=0;m<(1<<NV);m++){ int ok=1; for(int i=0;i<NV && ok;i++) if(((m>>i)&1) && (adj[i]&m)) ok=0; if(!ok) continue;
    int mx=1; for(int i=0;i<NV && mx;i++) if(!((m>>i)&1) && !(adj[i]&m)) mx=0; if(mx){ if(NPT>=64){ fprintf(stderr,"universe too large\n"); return 1; } pts[NPT++]=m; } }
  ALL = NPT==64 ? ~0ULL : ((1ULL<<NPT)-1); F=(1ULL<<NE)-1;
  u64 X[16]; for(int i=0;i<NV;i++){ X[i]=0; for(int j=0;j<NPT;j++) if((pts[j]>>i)&1) X[i]|=1ULL<<j; }
  // automorphisms by brute force over permutations (n <= 10)
  if(SYM){ int p[16]; for(int i=0;i<NV;i++) p[i]=i;
    for(;;){ int ok=1, id=1; for(int i=0;i<NV;i++) if(p[i]!=i) id=0;
      for(int e=0;e<NE && ok;e++) if(!((adj[p[ea[e]]]>>p[eb[e]])&1)) ok=0;
      if(ok && !id && nAut<64){ for(int j=0;j<NPT;j++){ int m=0; for(int i=0;i<NV;i++) if((pts[j]>>i)&1) m|=1<<p[i]; int q=-1; for(int t=0;t<NPT;t++) if(pts[t]==m) q=t; autp[nAut][j]=q; } nAut++; }
      int i=NV-2; while(i>=0 && p[i]>p[i+1]) i--; if(i<0) break; int j=NV-1; while(p[j]<p[i]) j--; int t=p[i]; p[i]=p[j]; p[j]=t;
      for(int a=i+1,b=NV-1;a<b;a++,b--){ t=p[a]; p[a]=p[b]; p[b]=t; } } }
  u64 L[MAXL]; int n=0; for(int i=0;i<NV;i++) if(adj[i]) L[n++]=X[i];
  printf("vertices %d edges %d universe %d points, automorphisms used %d, mode %d\n",NV,NE,NPT,nAut,MODE); fflush(stdout);
  canon(L,n);
  for(int N=lo;N<=hi;N++){ depth=0; nodes=hits=0; int ok=dfs(L,n,N);
    printf("N=%d %s nodes=%llu tt-hits=%llu stored=%llu\n",N,ok?"FOUND":"none",(unsigned long long)nodes,(unsigned long long)hits,(unsigned long long)stored); fflush(stdout);
    if(ok){ static const char *nm[4]={"and","or","andnot","notand"};
      if(SYM){ printf("  (rerun with sym 0 at this N to print the circuit)\n"); break; }
      u64 W[96]; int nw=0; for(int i=0;i<NV;i++) W[nw++]=X[i];
      for(int d=0;d<depth;d++){ int ia=-1, ib=-1; for(int t=0;t<nw;t++){ if(W[t]==path[d].a) ia=t; if(W[t]==path[d].b) ib=t; }
        printf("  w%d = %s [%d, %d]\n",nw,nm[path[d].op],ia,ib); W[nw++]=path[d].c; }
      break; } }
  return 0; }
