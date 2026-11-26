// All least fan-in-2 AND/OR circuits for the edge function of a small graph, tabulated by their number of
// dirty AND gates (AND gates true at some independent set: the "junk" of the project).
// usage: allmin n gates u1 v1 u2 v2 ...     (gates = the least size; found with mincirc)
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
typedef uint64_t V;
static int n, G, nd, ne; static V w[64], target, full, mismask; static int ga[64], gb[64], gop[64], used[64];
static long long count[16], total; static int shown[16];
static int key(int i){ return (gb[i]<<12)|(ga[i]<<2)|gop[i]; }
static void show(int d){ printf("example with %d dirty AND gate(s):\n", d); for(int i=n;i<n+G;i++) printf("  w%d = %s(w%d,w%d)%s\n", i, gop[i]?"OR":"AND", ga[i], gb[i], (!gop[i] && (w[i]&mismask))?"   <- dirty":""); }
static void dfs(int i, int unused){
  int rem = n+G-i;
  if (unused - rem > 1) return;
  for (int b=1;b<i;b++) for (int a=0;a<b;a++) for (int op=0;op<2;op++){
    V v = op ? (w[a]|w[b]) : (w[a]&w[b]);
    if (rem==1){ if (v!=target) continue; }
    else { if (v==0||v==full) continue; int dup=0; for(int k=0;k<i;k++) if(w[k]==v){dup=1;break;} if(dup) continue; }
    ga[i]=a; gb[i]=b; gop[i]=op;
    if (i>n && a!=i-1 && b!=i-1 && key(i)<key(i-1)) continue;
    int nu = unused + 1 - (used[a]?0:1) - (used[b]?0:1);
    if (rem==1){ if (nu==1){ w[i]=v; int d=0; for(int k=n;k<n+G;k++) if(!gop[k] && (w[k]&mismask)) d++; count[d]++; total++; if(!shown[d]){ shown[d]=1; show(d); } } continue; }
    used[a]++; used[b]++; w[i]=v; used[i]=0;
    dfs(i+1, nu);
    used[a]--; used[b]--;
  }
}
int main(int argc, char**argv){
  n=atoi(argv[1]); G=atoi(argv[2]); int m=(argc-3)/2; int adj[16]={0}, eu[64], ev[64];
  for(int k=0;k<m;k++){ eu[k]=atoi(argv[3+2*k]); ev[k]=atoi(argv[4+2*k]); adj[eu[k]]|=1<<ev[k]; adj[ev[k]]|=1<<eu[k]; }
  int dec[64]; nd=0; for(int k=0;k<m;k++) dec[nd++]=(1<<eu[k])|(1<<ev[k]); ne=nd;
  for(int s=0;s<(1<<n);s++){ int ok=1; for(int v=0;v<n&&ok;v++) if((s>>v&1)&&(adj[v]&s)) ok=0; if(!ok) continue;
    int mx=1; for(int v=0;v<n&&mx;v++) if(!(s>>v&1)&&!(adj[v]&s)) mx=0; if(mx) dec[nd++]=s; }
  for(int v=0;v<n;v++){ w[v]=0; for(int k=0;k<nd;k++) if(dec[k]>>v&1) w[v]|=(V)1<<k; used[v]=0; }
  target=((V)1<<ne)-1; full=((V)1<<nd)-1; mismask=full&~target;
  dfs(n, n);
  printf("n=%d edges=%d gates=%d: %lld least circuits (up to reordering of independent gates); by number of dirty ANDs:", n, m, G, total);
  for(int d=0;d<16;d++) if(count[d]) printf(" %d:%lld", d, count[d]); printf("\n"); return 0;
}
