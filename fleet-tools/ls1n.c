// local search: fan-in-2 AND/OR circuit with exactly one NOT gate (G gates in all), 7 inputs, full 128-bit tables
// usage: ls1n G seed seconds u1 v1 ...
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include <math.h>
typedef unsigned __int128 V;
#define N 7
static int G; static V w[64], target; static int ga[64], gb[64], gop[64], np;
static uint64_t s[2];
static inline uint64_t rnd(void){ uint64_t a=s[0], b=s[1]; s[0]=b; a^=a<<23; s[1]=a^b^(a>>17)^(b>>26); return s[1]+b; }
static inline int pc(V v){ return __builtin_popcountll((uint64_t)v)+__builtin_popcountll((uint64_t)(v>>64)); }
static inline int eval(void){ for(int i=N;i<N+G;i++) w[i]= gop[i]==2 ? ~w[ga[i]] : gop[i] ? (w[ga[i]]|w[gb[i]]) : (w[ga[i]]&w[gb[i]]); return pc(w[N+G-1]^target); }
static void show(void){ for(int i=N;i<N+G;i++){ if(gop[i]==2) printf("w%d = NOT(w%d)\n",i,ga[i]); else printf("w%d = %s(w%d,w%d)\n", i, gop[i]?"OR":"AND", ga[i], gb[i]); } }
int main(int argc,char**argv){
  G=atoi(argv[1]); s[0]=atoll(argv[2])*0x9E3779B97F4A7C15ULL+1; s[1]=0xD1B54A32D192ED03ULL^atoll(argv[2]); double secs=atof(argv[3]);
  int m=(argc-4)/2; target=0;
  for(int x=0;x<128;x++){ for(int v=0;v<N;v++) if(x>>v&1) w[v]|=(V)1<<x; int f=0; for(int k=0;k<m;k++){int u=atoi(argv[4+2*k]),v=atoi(argv[5+2*k]); if((x>>u&1)&&(x>>v&1)) f=1;} if(f) target|=(V)1<<x; }
  time_t t0=time(0); long long it=0; int best=999;
  while(difftime(time(0),t0)<secs){
    for(int i=N;i<N+G;i++){ gop[i]=rnd()&1; ga[i]=rnd()%i; gb[i]=rnd()%i; }
    np=N+rnd()%(G-1); gop[np]=2;
    int f=eval(); double T=2.0;
    for(long long step=0; step<3000000; step++){
      it++; int i=N+rnd()%G; int oa=ga[i], ob=gb[i], oo=gop[i], onp=np; int r=rnd()%4;
      if(r==3){ if(i==np||i==N+G-1){continue;} gop[np]=rnd()&1; gop[i]=2; np=i; }   // move the NOT
      else if(r==0){ if(i==np) continue; gop[i]^=1; } else if(r==1) ga[i]=rnd()%i; else gb[i]=rnd()%i;
      int f2=eval();
      if(f2<=f || (double)(rnd()>>11)*(1.0/9007199254740992.0) < exp((f-f2)/T)) { f=f2; if(f<best) best=f; if(f==0){ printf("FOUND G=%d seed=%s after %lld evals\n",G,argv[2],it); show(); return 0; } }
      else { if(r==3){ gop[onp]=2; np=onp; } ga[i]=oa; gb[i]=ob; gop[i]=oo; if(r==3) gop[onp]=2; }
      if((step&65535)==0){ T*=0.93; if(T<0.15) T=0.15; }
    }
  }
  printf("none G=%d seed=%s best_error=%d evals=%lld\n",G,argv[2],best,it); return 1;
}
