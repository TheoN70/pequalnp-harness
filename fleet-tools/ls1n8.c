// Local search: fan-in-2 AND/OR circuit with exactly one NOT gate (G gates in all) for the edge function of a graph
// on N <= 8 vertices, full truth tables (256 bits). mode 0 = no NOT at all (AND/OR only).
// usage: ls1n8 <N> <mode 0|1> <G> <seed> <seconds> u1 v1 u2 v2 ...
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include <math.h>
typedef struct { uint64_t a[4]; } V;
static int N, G, mode; static V w[80], target; static int ga[80], gb[80], gop[80], np;
static uint64_t s[2];
static inline uint64_t rnd(void){ uint64_t a=s[0], b=s[1]; s[0]=b; a^=a<<23; s[1]=a^b^(a>>17)^(b>>26); return s[1]+b; }
static inline int eval(void){
  for(int i=N;i<N+G;i++){ V *x=&w[ga[i]], *y=&w[gb[i]], *z=&w[i];
    if(gop[i]==2) for(int k=0;k<4;k++) z->a[k]=~x->a[k]; else if(gop[i]) for(int k=0;k<4;k++) z->a[k]=x->a[k]|y->a[k]; else for(int k=0;k<4;k++) z->a[k]=x->a[k]&y->a[k]; }
  int d=0; for(int k=0;k<4;k++) d+=__builtin_popcountll(w[N+G-1].a[k]^target.a[k]); return d; }
static void show(void){ for(int i=N;i<N+G;i++){ if(gop[i]==2) printf("w%d = NOT(w%d)\n",i,ga[i]); else printf("w%d = %s(w%d,w%d)\n", i, gop[i]?"OR":"AND", ga[i], gb[i]); } }
int main(int argc,char**argv){
  N=atoi(argv[1]); mode=atoi(argv[2]); G=atoi(argv[3]); s[0]=atoll(argv[4])*0x9E3779B97F4A7C15ULL+1; s[1]=0xD1B54A32D192ED03ULL^atoll(argv[4]); double secs=atof(argv[5]);
  int m=(argc-6)/2;
  for(int x=0;x<256;x++){ for(int v=0;v<N;v++) if(x>>v&1) w[v].a[x>>6]|=1ULL<<(x&63); int f=0;
    for(int k=0;k<m;k++){int u=atoi(argv[6+2*k]),v=atoi(argv[7+2*k]); if((x>>u&1)&&(x>>v&1)) f=1;} if(f) target.a[x>>6]|=1ULL<<(x&63); }
  time_t t0=time(0); long long it=0; int best=999;
  while(difftime(time(0),t0)<secs){
    for(int i=N;i<N+G;i++){ gop[i]=rnd()&1; ga[i]=rnd()%i; gb[i]=rnd()%i; }
    np=-1; if(mode){ np=N+rnd()%(G-1); gop[np]=2; }
    int f=eval(); double T=3.0;
    for(long long step=0; step<3000000; step++){
      it++; int i=N+rnd()%G; int oa=ga[i], ob=gb[i], oo=gop[i], onp=np; int r=rnd()%(mode?4:3);
      if(r==3){ if(i==np||i==N+G-1) continue; gop[np]=rnd()&1; gop[i]=2; np=i; }
      else if(r==0){ if(i==np) continue; gop[i]^=1; } else if(r==1) ga[i]=rnd()%i; else gb[i]=rnd()%i;
      int onpop = (r==3) ? gop[onp] : 0;
      int f2=eval();
      if(f2<=f || (double)(rnd()>>11)*(1.0/9007199254740992.0) < exp((f-f2)/T)) { f=f2; if(f<best) best=f; if(f==0){ printf("FOUND mode=%d G=%d seed=%s after %lld evals\n",mode,G,argv[4],it); show(); return 0; } }
      else { ga[i]=oa; gb[i]=ob; gop[i]=oo; if(r==3){ gop[onp]=2; np=onp; } (void)onpop; }
      if((step&65535)==0){ T*=0.93; if(T<0.2) T=0.2; }
    }
  }
  printf("none mode=%d G=%d seed=%s best_error=%d evals=%lld\n",mode,G,argv[4],best,it); return 1;
}
