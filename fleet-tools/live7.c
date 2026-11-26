// Exact circuit size of a graph function (OR over edges of x_a AND x_b) on up to 7 inputs, by the same
// live-wire search as live.c, with 128-bit tables and no symmetry reduction (so the printed steps are a real circuit).
// mode 0: AND, OR.  mode 1: signed (a&b, a|b, a&~b, b&~a), NOT free.
// usage: live7 <n inputs> <edges like 0-4,1-4,...> <mode> <N from> <N to> [log2 table]
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef unsigned __int128 u128; typedef uint64_t u64;
#define MAXL 24
static u128 F, ALL; static int MODE, NI, NP;
static int nT, T[128], nMin, Mn[128];
static u64 nodes, hits, stored;
static void sortw(u128 *a, int n){ for(int i=1;i<n;i++){ u128 v=a[i]; int j=i-1; while(j>=0 && a[j]>v){a[j+1]=a[j]; j--;} a[j+1]=v; } }
static int separated(const u128 *L, int n){
  if(MODE==0){ for(int k=0;k<nMin;k++){ int a=Mn[k]; u128 B=ALL; for(int i=0;i<n;i++) if((L[i]>>a)&1) B&=L[i]; if(B & ~F & ALL) return 0; } return 1; }
  for(int k=0;k<nT;k++){ int a=T[k]; u128 D=ALL; for(int i=0;i<n;i++) D &= ((L[i]>>a)&1) ? L[i] : ~L[i]; if(D & ~F & ALL) return 0; }
  return 1; }
typedef struct { u64 k1,k2; } Key;
static Key *tab; static uint8_t *tabr; static u64 TABMASK;
static inline u64 mix(u64 x){ x^=x>>33; x*=0xff51afd7ed558ccdULL; x^=x>>33; x*=0xc4ceb9fe1a85ec53ULL; x^=x>>33; return x; }
static inline Key hkey(const u128 *L, int n){ Key k; k.k1=0x9E3779B97F4A7C15ULL^n; k.k2=0xD1B54A32D192ED03ULL+n;
  for(int i=0;i<n;i++){ u64 lo=(u64)L[i], hi=(u64)(L[i]>>64);
    k.k1=mix(k.k1^lo)+0x165667B19E3779F9ULL; k.k1=mix(k.k1^hi)+0x27D4EB2F165667C5ULL;
    k.k2=mix((k.k2+lo)*0x2545F4914F6CDD1DULL)^(hi>>7); k.k2=mix((k.k2+hi)*0x9FB21C651E98DF25ULL)^(lo>>9); }
  if(!k.k1 && !k.k2) k.k1=1; return k; }
static int tt_failed(Key k, int r){ u64 i=k.k1&TABMASK; for(;;){ if(!tab[i].k1 && !tab[i].k2) return 0;
    if(tab[i].k1==k.k1 && tab[i].k2==k.k2) return tabr[i]>=r; i=(i+1)&TABMASK; } }
static void tt_store(Key k, int r){ u64 i=k.k1&TABMASK; for(;;){ if(!tab[i].k1 && !tab[i].k2){ tab[i]=k; tabr[i]=r; stored++;
      if(stored > (TABMASK>>1)+(TABMASK>>2)){ fprintf(stderr,"table full\n"); exit(2);} return; }
    if(tab[i].k1==k.k1 && tab[i].k2==k.k2){ if(tabr[i]<r) tabr[i]=r; return; } i=(i+1)&TABMASK; } }
typedef struct { u128 a,b,c; int op,keep; } Step;
static Step path[64]; static int depth;
static int dfs(const u128 *L, int n, int r){
  nodes++;
  Key k=hkey(L,n); if(tt_failed(k,r)){ hits++; return 0; }
  int nops = MODE==0 ? 2 : 4;
  for(int i=0;i<n;i++) for(int j=i+1;j<n;j++){ u128 a=L[i], b=L[j];
    for(int op=0;op<nops;op++){ u128 c = (op==0 ? (a&b) : op==1 ? (a|b) : op==2 ? (a&~b) : (b&~a)) & ALL;
      if(c==0 || c==ALL || c==a || c==b) continue;
      int dup=0; for(int t=0;t<n;t++) if(L[t]==c){dup=1;break;} if(dup) continue;
      for(int keep=0;keep<4;keep++){ int n2=n-2+(keep&1)+((keep>>1)&1)+1;
        path[depth]=(Step){a,b,c,op,keep};
        if(n2==1){ if(c==F){ depth++; return 1; } continue; }
        if(r-1<=0 || n2>r) continue;
        u128 L2[MAXL]; int m=0; for(int t=0;t<n;t++){ if(t==i && !(keep&1)) continue; if(t==j && !(keep&2)) continue; L2[m++]=L[t]; } L2[m++]=c;
        if(!separated(L2,m)) continue;
        sortw(L2,m); depth++; if(dfs(L2,m,r-1)) return 1; depth--; } } }
  tt_store(k,r); return 0; }
int main(int argc, char **argv){
  if(argc<6){ fprintf(stderr,"usage: live7 <n inputs> <edges 0-4,1-4,...> <mode> <N from> <N to> [log2 table]\n"); return 1; }
  NI=atoi(argv[1]); NP=1<<NI; ALL = NI==7 ? ~(u128)0 : (((u128)1<<NP)-1);
  int ea[64], eb[64], ne=0; { char *s=strdup(argv[2]); for(char *t=strtok(s,","); t; t=strtok(0,",")){ sscanf(t,"%d-%d",&ea[ne],&eb[ne]); ne++; } }
  MODE=atoi(argv[3]); int lo=atoi(argv[4]), hi=atoi(argv[5]);
  int lg = argc>6 ? atoi(argv[6]) : 24; TABMASK=(1ULL<<lg)-1; tab=calloc(TABMASK+1,sizeof(Key)); tabr=calloc(TABMASK+1,1);
  u128 X[7]; for(int i=0;i<NI;i++){ X[i]=0; for(int m=0;m<NP;m++) if((m>>i)&1) X[i]|=(u128)1<<m; }
  F=0; for(int m=0;m<NP;m++){ int v=0; for(int e=0;e<ne;e++) if(((m>>ea[e])&1) && ((m>>eb[e])&1)) v=1; if(v) F|=(u128)1<<m; }
  for(int a=0;a<NP;a++) if((F>>a)&1){ T[nT++]=a; int minimal=1; for(int i=0;i<NI;i++) if(((a>>i)&1) && ((F>>(a&~(1<<i)))&1)) minimal=0; if(minimal) Mn[nMin++]=a; }
  u128 L[MAXL]; int n=0; for(int i=0;i<NI;i++){ int used=0; for(int e=0;e<ne;e++) if(ea[e]==i||eb[e]==i) used=1; if(used) L[n++]=X[i]; }
  printf("edges %d true points %d minimal %d inputs %d mode %d\n",ne,nT,nMin,n,MODE);
  sortw(L,n);
  for(int N=lo;N<=hi;N++){ depth=0; nodes=hits=0; int ok=dfs(L,n,N);
    printf("N=%d %s nodes=%llu tt-hits=%llu stored=%llu\n",N,ok?"FOUND":"none",(unsigned long long)nodes,(unsigned long long)hits,(unsigned long long)stored); fflush(stdout);
    if(ok){ static const char *nm[4]={"and","or","andnot","notand"};
      // print as a circuit: wires 0..NI-1 inputs, then gates in order
      u128 W[64]; int nw=0; for(int i=0;i<NI;i++) W[nw++]=X[i];
      for(int d=0;d<depth;d++){ int ia=-1, ib=-1; for(int t=0;t<nw;t++){ if(W[t]==path[d].a) ia=t; if(W[t]==path[d].b) ib=t; }
        printf("  w%d = %s [%d, %d]\n",nw,nm[path[d].op],ia,ib); W[nw++]=path[d].c; }
      break; } }
  return 0; }
