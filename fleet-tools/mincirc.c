// Smallest fan-in-2 AND/OR circuit (every gate counted) for the edge function of a small graph.
// Wires are bit vectors over the decisive inputs (edges = must be 1, maximal independent sets = must be 0);
// for monotone circuits being right on those is being right everywhere.
// usage: mincirc n maxgates u1 v1 u2 v2 ...
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
typedef uint64_t V;
static int n, G, nd; static V w[64], target, full; static int ga[64], gb[64], gop[64], used[64];
static long long nodes; static int found;
static int key(int i){ return (gb[i]<<12)|(ga[i]<<2)|gop[i]; }
static void show(void){ for(int i=n;i<n+G;i++) printf("  w%d = %s(w%d,w%d)\n", i, gop[i]?"OR":"AND", ga[i], gb[i]); }
static void dfs(int i, int unused){            // i = index of the wire to create
  int rem = n+G-i;                              // gates still to place, this one included
  if (unused - rem > 1) return;
  for (int b=1;b<i;b++) for (int a=0;a<b;a++) for (int op=0;op<2;op++){
    V v = op ? (w[a]|w[b]) : (w[a]&w[b]);
    if (rem==1){ if (v!=target) continue; }
    else { if (v==0||v==full) continue; int dup=0; for(int k=0;k<i;k++) if(w[k]==v){dup=1;break;} if(dup) continue; }
    ga[i]=a; gb[i]=b; gop[i]=op;
    if (i>n && a!=i-1 && b!=i-1 && key(i)<key(i-1)) continue;   // adjacent independent gates in increasing order
    int ua=used[a], ub=used[b]; int nu = unused + 1 - (ua?0:1) - (ub?0:1);
    if (rem==1){ if (nu==1){ found=1; printf("FOUND with %d gates:\n", G); show(); return; } continue; }
    used[a]++; used[b]++; w[i]=v; used[i]=0; nodes++;
    dfs(i+1, nu);
    used[a]--; used[b]--;
    if (found) return;
  }
}
int main(int argc, char**argv){
  n=atoi(argv[1]); int maxg=atoi(argv[2]); int m=(argc-3)/2; int adj[16]={0}, eu[64], ev[64];
  for(int k=0;k<m;k++){ eu[k]=atoi(argv[3+2*k]); ev[k]=atoi(argv[4+2*k]); adj[eu[k]]|=1<<ev[k]; adj[ev[k]]|=1<<eu[k]; }
  int dec[64]; nd=0; for(int k=0;k<m;k++) dec[nd++]=(1<<eu[k])|(1<<ev[k]); int ne=nd, alpha=0;
  for(int s=0;s<(1<<n);s++){ int ok=1; for(int v=0;v<n&&ok;v++) if((s>>v&1)&&(adj[v]&s)) ok=0; if(!ok) continue;
    int c=__builtin_popcount(s); if(c>alpha) alpha=c;
    int mx=1; for(int v=0;v<n&&mx;v++) if(!(s>>v&1)&&!(adj[v]&s)) mx=0; if(mx){ if(nd>=64){printf("too many decisive inputs\n");return 1;} dec[nd++]=s; } }
  for(int v=0;v<n;v++){ w[v]=0; for(int k=0;k<nd;k++) if(dec[k]>>v&1) w[v]|=(V)1<<k; used[v]=0; }
  target=((V)1<<ne)-1; full=(nd==64)?~(V)0:(((V)1<<nd)-1);
  printf("n=%d edges=%d tau=%d bound E+tau-1=%d decisive=%d\n", n, m, n-alpha, m+n-alpha-1, nd);
  for(G=n-1; G<=maxg; G++){ nodes=0; found=0; dfs(n, n); printf("gates=%d: %s (nodes %lld)\n", G, found?"YES":"no", nodes); fflush(stdout); if(found) break; }
  return 0;
}
