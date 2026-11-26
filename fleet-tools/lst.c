// local search for a fan-in-2 circuit with G gates for a truth table on N<=7 inputs.
// usage: lst mode G seed seconds N tableHi tableLo   (table = Hi*2^64+Lo ; mode 0 = AND/OR, 1 = AND/OR/NOT)
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include <math.h>
typedef unsigned __int128 V;
static int N, G, mode; static V w[64], target, mask; static int ga[64], gb[64], gop[64];
static uint64_t s[2];
static inline uint64_t rnd(void){ uint64_t a=s[0], b=s[1]; s[0]=b; a^=a<<23; s[1]=a^b^(a>>17)^(b>>26); return s[1]+b; }
static inline int pc(V v){ return __builtin_popcountll((uint64_t)v)+__builtin_popcountll((uint64_t)(v>>64)); }
static inline int eval(void){ for(int i=N;i<N+G;i++) w[i]= gop[i]==2 ? ~w[ga[i]] : gop[i] ? (w[ga[i]]|w[gb[i]]) : (w[ga[i]]&w[gb[i]]); return pc((w[N+G-1]^target)&mask); }
static void show(void){ for(int i=N;i<N+G;i++){ if(gop[i]==2) printf("w%d = NOT(w%d)\n",i,ga[i]); else printf("w%d = %s(w%d,w%d)\n", i, gop[i]?"OR":"AND", ga[i], gb[i]); } }
static inline int rop(void){ return mode && rnd()%5==0 ? 2 : (int)(rnd()&1); }
int main(int argc,char**argv){
  mode=atoi(argv[1]); G=atoi(argv[2]); s[0]=atoll(argv[3])*0x9E3779B97F4A7C15ULL+1; s[1]=0xD1B54A32D192ED03ULL^atoll(argv[3]); double secs=atof(argv[4]);
  N=atoi(argv[5]); target=((V)strtoull(argv[6],0,10)<<64)|strtoull(argv[7],0,10);
  mask = N==7 ? ~(V)0 : (((V)1)<<(1<<N))-1;
  for(int x=0;x<(1<<N);x++) for(int v=0;v<N;v++) if(x>>v&1) w[v]|=(V)1<<x;
  time_t t0=time(0); long long it=0; int best=999;
  while(difftime(time(0),t0)<secs){
    for(int i=N;i<N+G;i++){ gop[i]=rop(); ga[i]=rnd()%i; gb[i]=rnd()%i; }
    int f=eval(); double T=2.0;
    for(long long step=0; step<3000000; step++){
      it++; int i=N+rnd()%G; int oa=ga[i], ob=gb[i], oo=gop[i]; int r=rnd()%3;
      if(r==0) gop[i]=rop(); else if(r==1) ga[i]=rnd()%i; else gb[i]=rnd()%i;
      int f2=eval();
      if(f2<=f || (double)(rnd()>>11)*(1.0/9007199254740992.0) < exp((f-f2)/T)) { f=f2; if(f<best) best=f; if(f==0){ printf("FOUND mode=%d G=%d seed=%s after %lld evals\n",mode,G,argv[3],it); show(); return 0; } }
      else { ga[i]=oa; gb[i]=ob; gop[i]=oo; }
      if((step&65535)==0){ T*=0.93; if(T<0.15) T=0.15; }
    }
  }
  printf("none mode=%d G=%d seed=%s best_error=%d evals=%lld\n",mode,G,argv[3],best,it); return 1;
}
