// Stochastic local search for a fan-in-2 AND/OR/NOT circuit with G gates computing the Petersen edge function,
// with an 11th free input equal to NOT x0 (the setting of L-meta-1884). Wires are full truth tables (1024 bits).
// usage: lsn G seed seconds
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#include <math.h>
#define NI 11
#define W 16
static const int PE[15][2]={{0,1},{1,2},{2,3},{3,4},{4,0},{0,5},{1,6},{2,7},{3,8},{4,9},{5,7},{7,9},{9,6},{6,8},{8,5}};
static int G; static uint64_t w[64][W], target[W]; static int ga[64], gb[64], gop[64];   // gop: 0 AND, 1 OR, 2 NOT(ga)
static uint64_t s[2];
static inline uint64_t rnd(void){ uint64_t a=s[0], b=s[1]; s[0]=b; a^=a<<23; s[1]=a^b^(a>>17)^(b>>26); return s[1]+b; }
static inline int eval(void){
  for(int i=NI;i<NI+G;i++){ uint64_t *x=w[ga[i]], *y=w[gb[i]], *z=w[i];
    if(gop[i]==0) for(int k=0;k<W;k++) z[k]=x[k]&y[k]; else if(gop[i]==1) for(int k=0;k<W;k++) z[k]=x[k]|y[k]; else for(int k=0;k<W;k++) z[k]=~x[k]; }
  int d=0; uint64_t *o=w[NI+G-1]; for(int k=0;k<W;k++) d+=__builtin_popcountll(o[k]^target[k]); return d; }
static void show(void){ for(int i=NI;i<NI+G;i++){ if(gop[i]==2) printf("w%d = NOT(w%d)\n",i,ga[i]); else printf("w%d = %s(w%d,w%d)\n", i, gop[i]?"OR":"AND", ga[i], gb[i]); } }
int main(int argc,char**argv){
  G=atoi(argv[1]); s[0]=atoll(argv[2])*0x9E3779B97F4A7C15ULL+1; s[1]=0xD1B54A32D192ED03ULL^atoll(argv[2]); double secs=atof(argv[3]);
  memset(w,0,sizeof w); memset(target,0,sizeof target);
  for(int x=0;x<1024;x++){ for(int v=0;v<10;v++) if(x>>v&1) w[v][x>>6]|=1ULL<<(x&63); if(!(x&1)) w[10][x>>6]|=1ULL<<(x&63);
    int f=0; for(int e=0;e<15;e++) if((x>>PE[e][0]&1)&&(x>>PE[e][1]&1)) f=1; if(f) target[x>>6]|=1ULL<<(x&63); }
  time_t t0=time(0); long long it=0, restarts=0; int best=9999;
  while(difftime(time(0),t0)<secs){
    for(int i=NI;i<NI+G;i++){ gop[i]=rnd()%8==0?2:(rnd()&1); ga[i]=rnd()%i; gb[i]=rnd()%i; }
    int f=eval(); restarts++; double T=6.0;
    for(long long step=0; step<1500000; step++){
      it++; int i=NI+rnd()%G; int oa=ga[i], ob=gb[i], oo=gop[i]; int r=rnd()%4;
      if(r==0) gop[i]=(rnd()%6==0)?2:(rnd()&1); else if(r==1||gop[i]==2) ga[i]=rnd()%i; else gb[i]=rnd()%i;
      int f2=eval();
      if(f2<=f || (double)(rnd()>>11)*(1.0/9007199254740992.0) < exp((f-f2)/T)) { f=f2; if(f<best) best=f; if(f==0){ printf("FOUND G=%d seed=%s after %lld evals\n",G,argv[2],it); show(); return 0; } }
      else { ga[i]=oa; gb[i]=ob; gop[i]=oo; }
      if((step&32767)==0){ T*=0.93; if(T<0.3) T=0.3; }
    }
  }
  printf("none G=%d seed=%s best_error=%d evals=%lld restarts=%lld\n",G,argv[2],best,it,restarts); return 1;
}
