/* Read-only, fuel-aware route planner. All distances use the game's integer
   Round(distance) jump limit. A recharge is a planned stop, never a game write.
   Minimum number of jumps first; farthest feasible hop among those routes.
   Required[k][s] is the least fuel needed at s to reach the goal in <=k jumps,
   with refuelling available only on eligible planets. No greedy dead ends. */
#define RP_STARS 4096
#define RP_HOPS 128
#define RP_EDGES 1048576
#define RP_INF 65535
typedef struct { float x,y; int recharge; } RPNode;
typedef struct { unsigned short to,cost,gain; } RPEdge;
typedef struct {
    RPNode nodes[RP_STARS];
    unsigned int offsets[RP_STARS+1];
    RPEdge edges[RP_EDGES];
    unsigned short required[RP_HOPS+1][RP_STARS];
    unsigned short path[RP_HOPS], fuelBefore[RP_HOPS];
    unsigned char refuel[RP_HOPS];
    int count, hops, refuels, engine, capacity, bonus,regen,accelerator;
} RP;
static double rp_sqrt(double x) {
    double r; __asm__("fsqrt" : "=t"(r) : "0"(x)); return r;
}
static double rp_sq(RPNode a,RPNode b) {
    double x=(double)a.x-b.x,y=(double)a.y-b.y;return x*x+y*y;
}
static int rp_round(double x) {
    int n=(int)x;double f=x-n;
    return n+(f>0.5 || (f==0.5 && (n&1)));
}
static int rp_hyper_days(int counter,int accelerator) {
    int days=0;
    while(counter>0) {
        --counter;
        if(counter>1) {counter-=accelerator;if(counter<1)counter=1;}
        ++days;
    }
    return days;
}
static int rp_gain(RP *p,double distance) {
    int counter=rp_round(distance/10.0)+1;if(counter<2)counter=2;
    int gain=p->regen*rp_hyper_days(counter,p->accelerator);
    return gain>p->capacity?p->capacity:gain;
}
static int rp_fill(RP *p,int fuel,int gain) {
    return fuel+gain>p->capacity?p->capacity:fuel+gain;
}
static int rp_need(RP *p,int cost,int next,int gain) {
    /* Fuel bonus gates a jump, but the game burns the full rounded distance
       and clamps the tank at zero. It is not a per-hop fuel discount. */
    next=next>gain?next-gain:0;
    int gate=cost-p->bonus;if(gate<0)gate=0;
    int continuation=next?cost+next:0;
    int before=gate>continuation?gate:continuation;
    if(before>p->capacity)return RP_INF;
    /* At least the gate's movement day regenerates fuel before the burn. */
    return before>p->regen?before-p->regen:0;
}
static int rp_build_graph(RP *p) {
    unsigned int end=0;
    for(int i=0;i<p->count;++i) {
        p->offsets[i]=end;
        for(int j=0;j<p->count;++j) {
            if(i==j)continue;
            double sq=rp_sq(p->nodes[i],p->nodes[j]);
            if(sq>=(p->engine+0.50001)*(p->engine+0.50001))continue;
            double distance=rp_sqrt(sq);int cost=rp_round(distance);
            if(cost>p->engine||rp_need(p,cost,0,0)>p->capacity)continue;
            if(end>=RP_EDGES)return -6;
            p->edges[end].to=j;p->edges[end].cost=cost;p->edges[end++].gain=rp_gain(p,distance);
        }
    }
    p->offsets[p->count]=end;return 0;
}
static int rp_plan(RP *p,int start,int goal,int fuel) {
    p->hops=0;p->refuels=0;
    if(p->count<=0||p->count>RP_STARS||start<0||goal<0||start>=p->count||goal>=p->count)return -6;
    if(start==goal)return 0;
    if(p->engine<=0||p->capacity<0||p->capacity>=RP_INF/2)return -2;
    /* A one-hop route needs no whole-galaxy graph, including very dense maps. */
    double directSq=rp_sq(p->nodes[start],p->nodes[goal]);
    if(directSq<(p->engine+0.50001)*(p->engine+0.50001)) {
        int cost=rp_round(rp_sqrt(directSq)),need=rp_need(p,cost,0,0);
        int available=p->nodes[start].recharge?p->capacity:fuel;
        if(cost<=p->engine&&need<=available) {
            int recharge=need>fuel;
            p->path[0]=goal;p->refuel[0]=recharge;p->refuels=recharge;
            p->fuelBefore[0]=rp_fill(p,recharge?p->capacity:fuel,p->regen);p->hops=1;return 0;
        }
    }
    int status=rp_build_graph(p);if(status)return status;
    for(int i=0;i<p->count;++i)p->required[0][i]=(i==goal)?0:RP_INF;
    int depth;
    for(depth=1;depth<=RP_HOPS;++depth) {
        int changed=0;
        for(int i=0;i<p->count;++i) {
            int best=p->required[depth-1][i];
            for(unsigned int e=p->offsets[i];e<p->offsets[i+1];++e) {
                RPEdge edge=p->edges[e];int tail=p->required[depth-1][edge.to];
                if(tail==RP_INF)continue;
                int need=rp_need(p,edge.cost,tail,edge.gain);
                if(need>p->capacity)continue;
                if(p->nodes[i].recharge)need=0;
                if(need<best)best=need;
            }
            p->required[depth][i]=best;
            if(best!=p->required[depth-1][i])changed=1;
        }
        if(p->required[depth][start]<=fuel)break;
        if(!changed)return -3;
    }
    if(depth>RP_HOPS)return -6;
    int at=start;
    while(at!=goal&&depth>0) {
        int available=p->nodes[at].recharge?p->capacity:fuel;
        int chosen=-1,cost=0,gain=0;double farthest=-1;
        for(unsigned int e=p->offsets[at];e<p->offsets[at+1];++e) {
            RPEdge edge=p->edges[e];int tail=p->required[depth-1][edge.to];
            if(tail==RP_INF||rp_need(p,edge.cost,tail,edge.gain)>available)continue;
            double distance=rp_sq(p->nodes[at],p->nodes[edge.to]);
            if(distance>farthest) {chosen=edge.to;cost=edge.cost;gain=edge.gain;farthest=distance;}
        }
        if(chosen<0)return -3;
        int tail=p->required[depth-1][chosen];
        int recharge=rp_need(p,cost,tail,gain)>fuel;
        if(recharge) {fuel=p->capacity;++p->refuels;}
        fuel=rp_fill(p,fuel,p->regen);
        int hop=p->hops++;
        p->path[hop]=chosen;p->fuelBefore[hop]=fuel;p->refuel[hop]=recharge;
        fuel=rp_fill(p,fuel>cost?fuel-cost:0,gain);at=chosen;--depth;
    }
    return at==goal?0:-3;
}
