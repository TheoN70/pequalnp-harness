// Stochastic local search for a fan-in-2 AND/OR circuit with G gates computing the edge function of a graph
// given on the command line. Wires are bit vectors over the decisive inputs (edges, maximal independent sets).
// lsr: same search for Represents (inputs with exactly one left and one right vertex on).
// usage: lsr G seed seconds n m <n*m chars 0/1, row u = left vertex u>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include <math.h>
typedef unsigned __int128 V;
static int N, G; static V w[80], target; static int ga[80], gb[80], gop[80];
static uint64_t s[2];
static inline uint64_t rnd(void){ uint64_t a=s[0], b=s[1]; s[0]=b; a^=a<<23; s[1]=a^b^(a>>17)^(b>>26); return s[1]+b; }
static inline int pc(V v){ return __builtin_popcountll((uint64_t)v)+__builtin_popcountll((uint64_t)(v>>64)); }
static inline int eval(void){ for(int i=N;i<N+G;i++) w[i]= gop[i] ? (w[ga[i]]|w[gb[i]]) : (w[ga[i]]&w[gb[i]]); return pc(w[N+G-1]^target); }
static void show(void){ for(int i=N;i<N+G;i++) printf("w%d = %s(w%d,w%d)\n", i, gop[i]?"OR":"AND", ga[i], gb[i]); }
int main(int argc,char**argv){
  G=atoi(argv[1]); s[0]=atoll(argv[2])*0x9E3779B97F4A7C15ULL+1; s[1]=0xD1B54A32D192ED03ULL^atoll(argv[2]); double secs=atof(argv[3]);
  int n=atoi(argv[4]), mm=atoi(argv[5]); const char*A=argv[6]; N=n+mm; int nd=0; target=0;
  // ponytail: one-hot points only (Represents), at most 128 of them
  if(n*mm>128||N>60){printf("too large\n");return 2;}
  for(int v=0;v<N;v++) w[v]=0;
  for(int u=0;u<n;u++) for(int v=0;v<mm;v++){ w[u]|=(V)1<<nd; w[n+v]|=(V)1<<nd; if(A[u*mm+v]=='1') target|=(V)1<<nd; nd++; }
  time_t t0=time(0); long long it=0, restarts=0; int best=999;
  while(difftime(time(0),t0)<secs){
    for(int i=N;i<N+G;i++){ gop[i]=rnd()&1; ga[i]=rnd()%i; gb[i]=rnd()%i; }
    int f=eval(); restarts++; double T=1.2;
    for(long long step=0; step<3000000; step++){
      it++; int i=N+rnd()%G; int oa=ga[i], ob=gb[i], oo=gop[i]; int r=rnd()%3;
      if(r==0) gop[i]^=1; else if(r==1) ga[i]=rnd()%i; else gb[i]=rnd()%i;
      int f2=eval();
      if(f2<=f || (double)(rnd()>>11)*(1.0/9007199254740992.0) < exp((f-f2)/T)) { f=f2; if(f<best) best=f; if(f==0){ printf("FOUND G=%d seed=%s after %lld evals\n",G,argv[2],it); show(); return 0; } }
      else { ga[i]=oa; gb[i]=ob; gop[i]=oo; }
      if((step&65535)==0){ T*=0.93; if(T<0.08) T=0.08; }
    }
  }
  printf("none G=%d seed=%s best_error=%d evals=%lld restarts=%lld\n",G,argv[2],best,it,restarts); return 1;
}
