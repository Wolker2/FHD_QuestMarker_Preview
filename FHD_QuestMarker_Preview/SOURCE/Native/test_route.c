#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "route_planner.h"
#include "route_geometry.h"
static RP p;
static void fixture(int n,int engine,int cap,int bonus) {
    p.count=n;p.engine=engine;p.capacity=cap;p.bonus=bonus;p.regen=0;p.accelerator=0;
    for(int i=0;i<n;++i)p.nodes[i]=(RPNode){0,0,0};
}
/* Independent state-space BFS oracle with fuel as an explicit state. */
static int oracle(int start,int goal,int fuel) {
    int seen[12][32],queue[4096][3],head=0,tail=0;
    for(int i=0;i<12;++i)for(int f=0;f<32;++f)seen[i][f]=0;
    queue[tail][0]=start;queue[tail][1]=fuel;queue[tail++][2]=0;seen[start][fuel]=1;
    while(head<tail) {
        int s=queue[head][0],f=queue[head][1],h=queue[head++][2];
        if(s==goal)return h;
        int available=p.nodes[s].recharge?p.capacity:f;
        available+=p.regen;if(available>p.capacity)available=p.capacity;
        for(int j=0;j<p.count;++j) {
            if(j==s)continue;
            double dx=(double)p.nodes[s].x-p.nodes[j].x,dy=(double)p.nodes[s].y-p.nodes[j].y;
            int cost=(int)nearbyint(sqrt(dx*dx+dy*dy));
            if(cost>p.engine||cost>available+p.bonus)continue;
            int left=available>cost?available-cost:0;
            int counter=(int)nearbyint(sqrt(dx*dx+dy*dy)/10.0)+1;if(counter<2)counter=2;
            int days=0;
            while(counter>0) {counter--;if(counter>1) {counter-=p.accelerator;if(counter<1)counter=1;}days++;}
            left+=p.regen*days;if(left>p.capacity)left=p.capacity;
            if(seen[j][left])continue;
            seen[j][left]=1;
            assert(tail<4096);queue[tail][0]=j;queue[tail][1]=left;queue[tail++][2]=h+1;
        }
    }
    return -1;
}
static void validate(int from,int goal,int fuel) {
    int refuels=0;
    for(int h=0;h<p.hops;++h) {
        int dest=p.path[h];
        if(p.refuel[h]) {assert(p.nodes[from].recharge);fuel=p.capacity;++refuels;}
        fuel+=p.regen;if(fuel>p.capacity)fuel=p.capacity;
        int cost=(int)nearbyint(sqrt(rp_sq(p.nodes[from],p.nodes[dest])));
        assert(cost<=p.engine&&cost<=fuel+p.bonus);
        assert(p.fuelBefore[h]==fuel);
        fuel=fuel>cost?fuel-cost:0;
        fuel+=rp_gain(&p,sqrt(rp_sq(p.nodes[from],p.nodes[dest])));
        if(fuel>p.capacity)fuel=p.capacity;
        from=dest;
    }
    assert(from==goal&&refuels==p.refuels);
}
int main(void) {
    fixture(4,10,10,0);
    p.nodes[0]=(RPNode){0,0,1};p.nodes[1]=(RPNode){-10,0,1};
    p.nodes[2]=(RPNode){9,0,1};p.nodes[3]=(RPNode){18,0,1};
    assert(rp_plan(&p,0,3,10)==0&&p.hops==2&&p.path[0]==2);validate(0,3,10);
    fixture(4,10,20,0);p.nodes[0]=(RPNode){0,0,1};p.nodes[1]=(RPNode){7,0,0};
    p.nodes[2]=(RPNode){10,0,0};p.nodes[3]=(RPNode){17,0,0};
    assert(rp_plan(&p,0,3,20)==0&&p.hops==2&&p.path[0]==2&&p.refuels==0);validate(0,3,20);
    fixture(3,10,10,0);p.nodes[0]=(RPNode){0,0,1};p.nodes[1]=(RPNode){10,0,0};p.nodes[2]=(RPNode){20,0,0};
    assert(rp_plan(&p,0,2,10)==-3);
    p.nodes[1].recharge=1;
    assert(rp_plan(&p,0,2,0)==0&&p.refuels==2);validate(0,2,0);
    fixture(3,10,10,3);p.nodes[0]=(RPNode){0,0,0};p.nodes[1]=(RPNode){10,0,0};p.nodes[2]=(RPNode){14,0,0};
    assert(rp_plan(&p,0,2,10)==-3); /* Bonus cannot be repeatedly subtracted from burn. */
    p.nodes[2].x=13;
    assert(rp_plan(&p,0,2,10)==0&&p.hops==2);validate(0,2,10);
    fixture(2,10,10,0);p.nodes[1].x=10.5f;
    assert(rp_plan(&p,0,1,10)==0);p.nodes[1].x=10.501f;assert(rp_plan(&p,0,1,10)==-3);
    assert(rp_plan(&p,0,0,0)==0&&p.hops==0);
    for(int trial=0;trial<5000;++trial) {
        int n=2+rand()%9,capacity=3+rand()%15;
        fixture(n,2+rand()%20,capacity,(rand()%6)-2);
        if(trial>=2500) {p.regen=rand()%4;p.accelerator=rand()%3;}
        for(int i=0;i<n;++i)p.nodes[i]=(RPNode){rand()%30,rand()%30,rand()%2};
        int fuel=rand()%(capacity+1),expect=oracle(0,n-1,fuel),actual=rp_plan(&p,0,n-1,fuel);
        if(expect<0)assert(actual==-3);
        else {assert(actual==0&&p.hops==expect);validate(0,n-1,fuel);}
    }
    RoutePoint a={-10,0},b={10,0};
    assert(fabs(rg_distance(a,b,0)-20)<1e-6);
    double expected=2*sqrt(100-25)+5*(acos(-1)-2*acos(.5));
    assert(fabs(rg_distance(a,b,5)-expected)<1e-6);
    assert(rg_days(a,b,5,10)==3);
    RoutePoint c={10,10};assert(fabs(rg_distance(b,c,5)-10)<1e-6);
    assert(rg_hyper_days(2,0)==2&&rg_hyper_days(5,0)==5);
    assert(rg_hyper_days(5,1)==3&&rg_hyper_days(5,2)==3&&rg_hyper_days(5,10)==2);
    puts("PASS: reachability, longest viable hops, fuel/refuelling, 5000 state-space oracle cases, stellar detours and hyperspace artefact time");
    return 0;
}
