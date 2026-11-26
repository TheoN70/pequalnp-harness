// lsd: lsg plus the Fano double re-read condition of L-meta-1479 (bipartite n=14 only, points 0..6, lines 7..13).
// Stochastic local search for a fan-in-2 AND/OR circuit with G gates computing the edge function of a graph
// given on the command line. Wires are bit vectors over the decisive inputs (edges, maximal independent sets).
// usage: lsg G seed seconds n u1 v1 u2 v2 ...
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include <math.h>
typedef unsigned __int128 V;
static int N, G; static V w[80], target; static int ga[80], gb[80], gop[80];
static uint64_t s[2]; static uint64_t bx[80],by[80],dv[80],dw[80],incm; static int wd=4;
static int dpen(void){ for(int i=N;i<N+G;i++){ int a=ga[i],b=gb[i]; if(gop[i]){ bx[i]=bx[a]|bx[b]; by[i]=by[a]|by[b]; dv[i]=dv[a]|dv[b]; dw[i]=dw[a]|dw[b]; } else { bx[i]=bx[a]&bx[b]; by[i]=by[a]&by[b]; dv[i]=(bx[a]&dv[b])|(dv[a]&bx[b]); dw[i]=(by[a]&dw[b])|(dw[a]&by[b]); } }
  int o=N+G-1; uint64_t bad=dv[o]|dw[o]; if(~bad&incm) return 0; int mn=99; for(int k=0;k<49;k++) if(incm>>k&1){ int c=(dv[o]>>k&1)+(dw[o]>>k&1); if(c<mn) mn=c; } return mn; }
static inline uint64_t rnd(void){ uint64_t a=s[0], b=s[1]; s[0]=b; a^=a<<23; s[1]=a^b^(a>>17)^(b>>26); return s[1]+b; }
static inline int pc(V v){ return __builtin_popcountll((uint64_t)v)+__builtin_popcountll((uint64_t)(v>>64)); }
static inline int eval(void){ for(int i=N;i<N+G;i++) w[i]= gop[i] ? (w[ga[i]]|w[gb[i]]) : (w[ga[i]]&w[gb[i]]); return 2*pc(w[N+G-1]^target)+wd*dpen(); }
static void show(void){ for(int i=N;i<N+G;i++) printf("w%d = %s(w%d,w%d)\n", i, gop[i]?"OR":"AND", ga[i], gb[i]); }
int main(int argc,char**argv){
  G=atoi(argv[1]); s[0]=atoll(argv[2])*0x9E3779B97F4A7C15ULL+1; s[1]=0xD1B54A32D192ED03ULL^atoll(argv[2]); double secs=atof(argv[3]);
  N=atoi(argv[4]); int m=(argc-5)/2, adj[20]={0}, dec[128], nd=0, alpha=0;
  for(int k=0;k<m;k++){ int u=atoi(argv[5+2*k]), v=atoi(argv[6+2*k]); adj[u]|=1<<v; adj[v]|=1<<u; dec[nd++]=(1<<u)|(1<<v); }
  for(int t=0;t<(1<<N);t++){ int ok=1; for(int v=0;v<N&&ok;v++) if((t>>v&1)&&(adj[v]&t)) ok=0; if(!ok) continue;
    int c=__builtin_popcount(t); if(c>alpha) alpha=c;
    int mx=1; for(int v=0;v<N&&mx;v++) if(!(t>>v&1)&&!(adj[v]&t)) mx=0; if(mx){ if(nd>=128){printf("too many decisive inputs\n");return 2;} dec[nd++]=t; } }
  for(int v=0;v<N;v++){ w[v]=0; for(int k=0;k<nd;k++) if(dec[k]>>v&1) w[v]|=(V)1<<k; }
  target=(((V)1)<<m)-1; if(atoi(argv[2])==1) printf("n=%d edges=%d tau=%d bound=%d decisive=%d\n",N,m,N-alpha,m+N-alpha-1,nd);
  incm=0; for(int p=0;p<7;p++) for(int l=0;l<7;l++) if((adj[p]>>(7+l))&1) incm|=1ULL<<(p*7+l);
  for(int v=0;v<14;v++){ bx[v]=by[v]=dv[v]=dw[v]=0; for(int p=0;p<7;p++) for(int l=0;l<7;l++){ int k=p*7+l; if(v==p) bx[v]|=1ULL<<k, dw[v]|=1ULL<<k; if(v==7+l) by[v]|=1ULL<<k, dv[v]|=1ULL<<k; } }
  time_t t0=time(0); long long it=0, restarts=0; int best=999;
  while(difftime(time(0),t0)<secs){
    for(int i=N;i<N+G;i++){ gop[i]=rnd()&1; ga[i]=rnd()%i; do gb[i]=rnd()%i; while(gb[i]==ga[i]); }
    int f=eval(); restarts++; double T=1.2;
    for(long long step=0; step<3000000; step++){
      it++; int i=N+rnd()%G; int oa=ga[i], ob=gb[i], oo=gop[i]; int r=rnd()%3;
      if(r==0) gop[i]^=1; else if(r==1) ga[i]=rnd()%i; else gb[i]=rnd()%i; if(ga[i]==gb[i]){ ga[i]=oa; gb[i]=ob; gop[i]=oo; continue; }
      int f2=eval();
      if(f2<=f || (double)(rnd()>>11)*(1.0/9007199254740992.0) < exp((f-f2)/T)) { f=f2; if(f<best) best=f; if(f==0){ printf("FOUND G=%d seed=%s after %lld evals\n",G,argv[2],it); show(); return 0; } }
      else { ga[i]=oa; gb[i]=ob; gop[i]=oo; }
      if((step&65535)==0){ T*=0.93; if(T<0.08) T=0.08; }
    }
  }
  printf("none G=%d seed=%s best_error=%d evals=%lld restarts=%lld\n",G,argv[2],best,it,restarts); return 1;
}
