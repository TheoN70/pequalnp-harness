// Stochastic local search for a fan-in-2 AND/OR circuit with G gates computing a monotone DNF on N <= 20 inputs.
// Wires are bit vectors over the decisive inputs (minimal true points, maximal false points); exact for monotone circuits.
// usage: lsdnf G seed seconds N term1 term2 ...   (each term = decimal bitmask of the variables ANDed)
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include <math.h>
typedef unsigned __int128 V;
static int N, G; static V w[200], target; static int ga[200], gb[200], gop[200];
static uint64_t s[2];
static inline uint64_t rnd(void){ uint64_t a=s[0], b=s[1]; s[0]=b; a^=a<<23; s[1]=a^b^(a>>17)^(b>>26); return s[1]+b; }
static inline int pc(V v){ return __builtin_popcountll((uint64_t)v)+__builtin_popcountll((uint64_t)(v>>64)); }
static inline int eval(void){ for(int i=N;i<N+G;i++) w[i]= gop[i] ? (w[ga[i]]|w[gb[i]]) : (w[ga[i]]&w[gb[i]]); return pc(w[N+G-1]^target); }
static void show(void){ for(int i=N;i<N+G;i++) printf("w%d = %s(w%d,w%d)\n", i, gop[i]?"OR":"AND", ga[i], gb[i]); }
static int m; static int term[64];
static int f(int t){ for(int k=0;k<m;k++) if((term[k]&t)==term[k]) return 1; return 0; }
int main(int argc,char**argv){
  G=atoi(argv[1]); s[0]=atoll(argv[2])*0x9E3779B97F4A7C15ULL+1; s[1]=0xD1B54A32D192ED03ULL^atoll(argv[2]); double secs=atof(argv[3]);
  N=atoi(argv[4]); m=argc-5; int dec[128], nd=0; target=0;
  for(int k=0;k<m;k++) term[k]=atoi(argv[5+k]);
  for(int t=0;t<(1<<N);t++){
    if(f(t)){ int mn=1; for(int v=0;v<N&&mn;v++) if((t>>v&1)&&f(t^(1<<v))) mn=0; if(!mn) continue; if(nd>=128){printf("too many\n");return 2;} target|=(V)1<<nd; dec[nd++]=t; }
    else { int mx=1; for(int v=0;v<N&&mx;v++) if(!(t>>v&1)&&!f(t|(1<<v))) mx=0; if(!mx) continue; if(nd>=128){printf("too many\n");return 2;} dec[nd++]=t; } }
  for(int v=0;v<N;v++){ w[v]=0; for(int k=0;k<nd;k++) if(dec[k]>>v&1) w[v]|=(V)1<<k; }
  if(atoi(argv[2])==1) printf("N=%d terms=%d decisive=%d true=%d\n",N,m,nd,pc(target));
  time_t t0=time(0); long long it=0, restarts=0; int best=999;
  while(difftime(time(0),t0)<secs){
    for(int i=N;i<N+G;i++){ gop[i]=rnd()&1; ga[i]=rnd()%i; gb[i]=rnd()%i; }
    int fv=eval(); restarts++; double T=1.2;
    for(long long step=0; step<3000000; step++){
      it++; int i=N+rnd()%G; int oa=ga[i], ob=gb[i], oo=gop[i]; int r=rnd()%3;
      if(r==0) gop[i]^=1; else if(r==1) ga[i]=rnd()%i; else gb[i]=rnd()%i;
      int f2=eval();
      if(f2<=fv || (double)(rnd()>>11)*(1.0/9007199254740992.0) < exp((fv-f2)/T)) { fv=f2; if(fv<best) best=fv; if(fv==0){ printf("FOUND G=%d seed=%s after %lld evals\n",G,argv[2],it); show(); return 0; } }
      else { ga[i]=oa; gb[i]=ob; gop[i]=oo; }
      if((step&65535)==0){ T*=0.93; if(T<0.08) T=0.08; }
    }
  }
  printf("none G=%d seed=%s best_error=%d evals=%lld restarts=%lld\n",G,argv[2],best,it,restarts); return 1;
}
