/* Included after the baseline native bridge. Delphi register ABI only here;
   exported ScriptLibs functions have no arguments, preserving its stack ABI. */
#include "route_planner.h"
#include "route_geometry.h"
static RP routePlan;
static u8 *routeStars[RP_STARS];
static u8 *routeRefuelPlanets[RP_HOPS];
static u8 *routeOrigin,*routePlayer,*routeGoal,*routePlanet;
static int routeDays,routeJumpDays,routeSystemDays,routeDockDays;
static int routeHooked;
static volatile int routeDisplayed,routeApplying,routeSession;
static volatile int routePending;
static u8 *routeLabel,*routeDeadlineLabel,*routeMarker;
static int routeDeadlineDays;
ptr routeOpenContinue,routeOpenTrampolinePtr;
ptr routePathContinue,routePathTrampolinePtr;
ptr routeMouseContinue,routeMouseTrampolinePtr;
static struct {u32 byteLength;u16 chars[1024];} routeSummary;
static struct {u32 byteLength;u16 chars[8192];} routeDetails;
static struct {u32 byteLength;u16 chars[64];} routeDeadline;
static const struct {u32 byteLength;u16 chars[18];} routeLabelName={34,
    {'F','H','D','Q','u','e','s','t','R','o','u','t','e','I','n','f','o',0}};
static const struct {u32 byteLength;u16 chars[22];} routeDeadlineName={42,
    {'F','H','D','Q','u','e','s','t','R','o','u','t','e','D','e','a','d','l','i','n','e',0}};
static const struct {u32 byteLength;u16 chars[17];} routeMarkerName={32,
    {'F','H','D','Q','u','e','s','t','M','a','r','k','V','0','3','5',0}};

static const struct {u32 byteLength;u16 chars[19];} routeFrameName={36,
    {'F','H','D','Q','u','e','s','t','R','o','u','t','e','F','r','a','m','e',0}};

static u32 route_call3(ptr fn,u32 a,u32 d,u32 c) {
    __asm__ volatile("call *%3":"+a"(a),"+d"(d),"+c"(c):"r"(fn):
        "memory","cc","st","st(1)","st(2)","st(3)","st(4)","st(5)","st(6)","st(7)");
    return a;
}
static u32 route_call(u32 rva,ptr a,ptr d,ptr c) {
    return route_call3(game+rva,(u32)a,(u32)d,(u32)c);
}
static u8 *route_player(void) {
    return (u8 *)route_call(0x38c078,0,0,0);
}
static int route_eligible(u8 *planet,u8 *player) {
    if(!planet||planet[0x15c]||(planet[0x74]>4&&planet[0x74]!=7))return 0;
    /* Native refuelling permits Coalition/Pirate planet owners and nonhostile
       relations. Nothing is purchased by this preview. */
    return (route_call(0x37d484,planet,player,0)&255)>0;
}
static u8 *route_first_refuel(u8 *star,u8 *player) {
    u8 *list=*(u8 **)(star+0x24);if(!list)return 0;
    int n=*(int *)(list+8);u8 **items=*(u8 ***)(list+4);
    if(n<0||n>512||(n&&!items))return 0;
    for(int i=0;i<n;++i)if(route_eligible(items[i],player))return items[i];
    return 0;
}
static void route_planet_point(u8 *planet,int elapsed,RoutePoint *out) {
    /* GetPosition reads the polar orbit. Predict an entire number of days on
       a private copy, independent of the destination star's step cache. */
    u8 copy[0x168];for(u32 i=0;i<sizeof(copy);++i)copy[i]=planet[i];
    *(double *)(copy+0x20)+=*(double *)(copy+0x40)*elapsed;
    route_call(0x379d1c,copy,out,0);
}
static int route_landing(u8 *planet,RoutePoint from,int elapsed,int speed,RoutePoint *out) {
    u8 *star=*(u8 **)(planet+0x18);double safe=*(float *)(star+0x5c);
    /* Search the earliest day whose flight budget reaches the moving planet;
       avoids oscillating fixed-point ETA on fast orbits. Docking takes a day. */
    for(int day=0;day<10000;++day) {
        route_planet_point(planet,elapsed+day,out);
        if(rg_distance(from,*out,safe)<=speed*(double)day+1) {
            route_planet_point(planet,elapsed+day+1,out);return day+1;
        }
    }
    return -1;
}
static void route_jump_point(u8 *origin,u8 *dest,int arrival,RoutePoint *out) {
    u8 proxy[0x104];for(u32 i=0;i<sizeof(proxy);++i)proxy[i]=routePlayer[i];
    *(u8 **)(proxy+0x24)=origin;
    route_call(arrival?0x31c590:0x31c4b4,proxy,dest,out);
}
static u8 *route_best_refuel(u8 *star,RoutePoint from,RoutePoint departure,int elapsed,int speed,int *days,RoutePoint *after) {
    u8 *list=*(u8 **)(star+0x24),*best=0;*days=0x7fffffff;
    int n=*(int *)(list+8);u8 **items=*(u8 ***)(list+4);
    for(int i=0;i<n;++i) {
        u8 *planet=items[i];if(!route_eligible(planet,routePlayer))continue;
        RoutePoint position;int land=route_landing(planet,from,elapsed,speed,&position);
        if(land<0)continue;
        route_planet_point(planet,elapsed+land+1,&position);
        int travel=rg_days(position,departure,*(float *)(star+0x5c),speed);
        int total=land+1+travel;
        if(total<*days) {best=planet;*days=total;*after=position;}
    }
    return best;
}
static int route_artifact_boost(int kind) {
    /* CanBoostArtefact has fourth Boolean argument on stack, callee ret 4. */
    u32 a=(u32)routePlayer,d=kind,c=0;
    ptr fn=game+0x325cb8;
    __asm__ volatile("pushl $0;call *%3":"+a"(a),"+d"(d),"+c"(c):"r"(fn):
        "memory","cc","st","st(1)","st(2)","st(3)","st(4)","st(5)","st(6)","st(7)");
    return a&255;
}
static int route_hyper_accelerator(void) {
    int boost=route_artifact_boost(34);
    int count=route_call(0x325a74,routePlayer,(ptr)34,0);
    return count*(boost+1);
}
static int route_fuel_regeneration(void) {
    int count=route_call(0x325a74,routePlayer,(ptr)11,0);
    if(count<=0)return 0;
    int base=*(int *)(game+0x489e28),extra=*(int *)(game+0x489e98);
    int regen=(base+extra*route_artifact_boost(11))*count;
    return regen>0?(regen>routePlan.capacity?routePlan.capacity:regen):0;
}
static void route_gate_points(u8 *star,u8 *dest,RoutePoint *departure,RoutePoint *arrival) {
    route_jump_point(star,dest,0,departure);
    route_jump_point(star,dest,1,arrival);
    /* Native gate begins up to 400 units before the map boundary; exit
       animation ends about 300 units inside the destination system. */
    double r=rp_sqrt((double)departure->x*departure->x+(double)departure->y*departure->y);
    if(r>400) {departure->x*=1-400/r;departure->y*=1-400/r;}
    r=rp_sqrt((double)arrival->x*arrival->x+(double)arrival->y*arrival->y);
    if(r>300) {arrival->x*=1-300/r;arrival->y*=1-300/r;}
}
static int route_hop_cost(u8 *a,u8 *b) {
    RPNode x={*(float *)(a+0x14),*(float *)(a+0x18),0};
    RPNode y={*(float *)(b+0x14),*(float *)(b+0x18),0};
    return rp_round(rp_sqrt(rp_sq(x,y)));
}
static int route_without_refuel(int first,u8 *star,RoutePoint position,int fuel,int speed) {
    /* Remove a planned stop only if natural regeneration reaches every hop
       through the next planned refuelling stop (or the final objective). */
    for(int i=first;i<routePlan.hops;++i) {
        if(i>first&&routePlan.refuel[i])return 1;
        u8 *dest=routeStars[routePlan.path[i]];RoutePoint departure,arrival;
        route_gate_points(star,dest,&departure,&arrival);
        int fly=rg_days(position,departure,*(float *)(star+0x5c),speed)+1;
        fuel=rp_fill(&routePlan,fuel,fly*routePlan.regen);
        int cost=route_hop_cost(star,dest);
        if(cost>fuel+routePlan.bonus)return 0;
        fuel=fuel>cost?fuel-cost:0;
        int counter=route_call(0x31c634,routePlayer,star,dest);
        int days=rg_hyper_days(counter,routePlan.accelerator);
        fuel=rp_fill(&routePlan,fuel,days*routePlan.regen);
        star=dest;position=arrival;
    }
    return 1;
}
static int route_estimate(int speed) {
    RoutePoint position=*(RoutePoint *)(routePlayer+0x14);
    u8 *docked=*(u8 **)(routePlayer+0x1c),*star=routeOrigin;
    routeDays=routeJumpDays=routeSystemDays=routeDockDays=0;
    u8 *tank=(u8 *)route_call(0x30e5fc,routePlayer,0,0);
    int fuel=*(int *)(tank+0x64);if(fuel<0)fuel=0;
    if(docked&&!(docked==routePlanet&&routePlan.hops==0)) {
        routeDays=routeDockDays=1;route_planet_point(docked,1,&position);
        fuel=rp_fill(&routePlan,fuel,routePlan.regen);
    }
    int accelerator=routePlan.accelerator;
    for(int i=0;i<routePlan.hops;++i) {
        u8 *dest=routeStars[routePlan.path[i]];RoutePoint departure,arrival;
        route_gate_points(star,dest,&departure,&arrival);
        if(routePlan.refuel[i]&&routePlan.regen>0&&route_without_refuel(i,star,position,fuel,speed)) {
            routePlan.refuel[i]=0;--routePlan.refuels;
        }
        if(routePlan.refuel[i]) {
            if(i==0&&docked&&route_eligible(docked,routePlayer)) {
                routeRefuelPlanets[i]=docked;
            } else {
                int detour;RoutePoint after;
                u8 *planet=route_best_refuel(star,position,departure,routeDays,speed,&detour,&after);
                if(!planet)return -3;
                int land=route_landing(planet,position,routeDays,speed,&after);
                routeDays+=land+1;routeDockDays+=2;routeSystemDays+=land-1;
                route_planet_point(planet,routeDays,&position);
                routeRefuelPlanets[i]=planet;
            }
            fuel=routePlan.capacity;
        } else routeRefuelPlanets[i]=0;
        int fly=rg_days(position,departure,*(float *)(star+0x5c),speed)+1;
        routeDays+=fly;routeSystemDays+=fly;
        fuel=rp_fill(&routePlan,fuel,fly*routePlan.regen);
        int cost=route_hop_cost(star,dest);
        if(cost>fuel+routePlan.bonus)return -3;
        fuel=fuel>cost?fuel-cost:0;
        int counter=route_call(0x31c634,routePlayer,star,dest);
        int jump=rg_hyper_days(counter,accelerator);
        routeDays+=jump;routeJumpDays+=jump;
        fuel=rp_fill(&routePlan,fuel,jump*routePlan.regen);
        position=arrival;star=dest;
    }
    if(routePlanet) {
        if(!(docked==routePlanet&&routePlan.hops==0)) {
            RoutePoint end;int landing=route_landing(routePlanet,position,routeDays,speed,&end);
            if(landing<0)return -6;
            routeDays+=landing;routeSystemDays+=landing-1;++routeDockDays;
        }
    }
    return 0;
}
static void route_append(u16 *buffer,int *at,int max,const u16 *text) {
    if(!text)return;
    for(int i=0;text[i]&&*at<max-1;++i)buffer[(*at)++]=text[i];
    buffer[*at]=0;
}
static void route_number(u16 *buffer,int *at,int max,int number) {
    u16 digits[16];int n=0;
    do {digits[n++]=48+number%10;number/=10;}while(number&&n<15);
    while(n&&*at<max-1)buffer[(*at)++]=digits[--n];
    buffer[*at]=0;
}
#include "route_text.h"
static void route_build_text(int speed) {
    int at=0;u16 *s=routeSummary.chars;
    route_append(s,&at,1024,routePlanet?txtLanding:txtSystem);
    route_number(s,&at,1024,routeDays);route_append(s,&at,1024,txtDays);
    route_number(s,&at,1024,routePlan.hops);route_append(s,&at,1024,txtJumps);
    route_number(s,&at,1024,routePlan.refuels);
    routeSummary.byteLength=at*2;
    at=0;
    static const u16 deadlineTitle[]={0x0421,0x0440,0x043e,0x043a,':',' ',0}; /* Срок: */
    static const u16 deadlineUnit[]={' ',0x0434,0x043d,'.',0}; /* дн. */
    route_append(routeDeadline.chars,&at,64,deadlineTitle);
    route_number(routeDeadline.chars,&at,64,routeDeadlineDays);
    route_append(routeDeadline.chars,&at,64,deadlineUnit);
    routeDeadline.byteLength=at*2;
    at=0;u16 *d=routeDetails.chars;
    route_append(d,&at,8192,s);route_append(d,&at,8192,txtBreakdown);
    route_number(d,&at,8192,routeJumpDays);route_append(d,&at,8192,txtInSystems);
    route_number(d,&at,8192,routeSystemDays);route_append(d,&at,8192,txtDocking);
    route_number(d,&at,8192,routeDockDays);route_append(d,&at,8192,txtSpeed);
    route_number(d,&at,8192,speed);route_append(d,&at,8192,txtRange);
    route_number(d,&at,8192,routePlan.engine);route_append(d,&at,8192,txtRegeneration);
    route_number(d,&at,8192,routePlan.regen);route_append(d,&at,8192,txtItinerary);
    route_append(d,&at,8192,*(u16 **)(routeOrigin+0x10));
    for(int i=0;i<routePlan.hops;++i) {
        if(routeRefuelPlanets[i]) {
            route_append(d,&at,8192,txtRefuel);
            route_append(d,&at,8192,*(u16 **)(routeRefuelPlanets[i]+0x14));
            route_append(d,&at,8192,txtParen);
        }
        route_append(d,&at,8192,txtArrow);
        route_append(d,&at,8192,*(u16 **)(routeStars[routePlan.path[i]]+0x10));
    }
    if(routePlanet) {
        route_append(d,&at,8192,txtTarget);route_append(d,&at,8192,*(u16 **)(routePlanet+0x14));
    }
    route_append(d,&at,8192,txtAssumptions);routeDetails.byteLength=at*2;
}
__attribute__((used)) void routePathChanged(u8 *screen) {
    (void)screen;
    if(routeApplying||!routeDisplayed)return;
    routeDisplayed=0;
    if(routeLabel)route_call(0x90104,routeLabel,0,0);
    if(routeDeadlineLabel) {
        route_call(0x90104,routeDeadlineLabel,0,0);
        route_call(0xc9eac,routeDeadlineLabel,0,0);
    }
    if(routeMarker)route_call(0xc9eac,routeMarker,0,0);
    routeLabel=0;
    routeDeadlineLabel=routeMarker=0;
}
__attribute__((used)) void routeApply(u8 *screen) {
    if(!routePending||!screen||screen[0x134])return;
    routePending=0;
    if(route_player()!=routePlayer||*(u8 **)(routePlayer+0x24)!=routeOrigin)return;
    u8 *list=*(u8 **)(screen+0x104);if(!list)return;
    routeApplying=1;
    route_call3(*(ptr *)(*(u8 **)list+8),(u32)list,0,0);
    *(u8 **)(screen+0x100)=routePlan.hops?routeStars[routePlan.path[0]]:routeGoal;
    for(int i=1;i<routePlan.hops;++i)route_call(0x161c0,list,routeStars[routePlan.path[i]],0);
    route_call(0x2a339c,screen,0,0);
    u8 *button=*(u8 **)(screen+0x11c);
    if(button)route_call(0xa1b30,button,(ptr)(!routePlan.hops||screen[0xd8]==1||routePlayer[0xdb9]),0);
    route_call(0x2a5078,screen,routeGoal,0);
    routeLabel=(u8 *)route_call(0xcefc8,screen,(ptr)routeLabelName.chars,0);
    if(routeLabel)route_call(0x90104,routeLabel,routeSummary.chars,0);
    routeDeadlineLabel=(u8 *)route_call(0xcefc8,screen,(ptr)routeDeadlineName.chars,0);
    if(routeDeadlineLabel) {
        route_call(0x90104,routeDeadlineLabel,routeDeadline.chars,0);
        route_call(0xc9eac,routeDeadlineLabel,(ptr)1,0);
    }
    routeMarker=(u8 *)route_call(0xcefc8,screen,(ptr)routeMarkerName.chars,0);
    if(routeMarker)route_call(0xc9eac,routeMarker,(ptr)1,0);
    routeApplying=0;routeDisplayed=routeSession=1;
}
/* The lower UI extends outside ImagePanel's old pixel hit area. Prevent
   native click-outside auto-close only for points inside this named extension. */
__attribute__((used)) int routePanelClick(u8 *screen,const int *point) {
    if(!screen||!point)return 0;
    u8 *frame=(u8 *)route_call(0xcefc8,screen,(ptr)routeFrameName.chars,0);
    if(!frame||!frame[0x41])return 0;
    const int *bounds=(const int *)(frame+0x60);
    return point[0]>=bounds[0]&&point[0]<bounds[2]&&point[1]>=bounds[1]&&point[1]<bounds[3];
}
NAKED static void routeMouseTrampoline(void) {
    __asm__ volatile(".intel_syntax noprefix;.byte 0x55,0x8b,0xec,0x83,0xc4,0xec;"
        "jmp DWORD PTR [routeMouseContinue];.att_syntax prefix;");
}
NAKED static void routeMouseHook(void) {
    __asm__ volatile(".intel_syntax noprefix;pushfd;pushad;mov eax,[esp+28];"
        "push DWORD PTR [esp+40];push eax;call routePanelClick;add esp,8;test eax,eax;"
        "jz 1f;popad;popfd;ret 4;1:popad;popfd;"
        "jmp DWORD PTR [routeMouseTrampolinePtr];.att_syntax prefix;");
}
NAKED static void routeOpenTrampoline(void) {
    __asm__ volatile(".intel_syntax noprefix;.byte 0x55,0x8b,0xec,0xb9,0x41,0,0,0;"
        "jmp DWORD PTR [routeOpenContinue];.att_syntax prefix;");
}
NAKED static void routeOpenHook(void) {
    __asm__ volatile(".intel_syntax noprefix;push ebx;mov ebx,eax;call DWORD PTR [routeOpenTrampolinePtr];"
        "pushfd;pushad;push ebx;call routeApply;add esp,4;popad;popfd;pop ebx;ret;.att_syntax prefix;");
}
NAKED static void routePathTrampoline(void) {
    __asm__ volatile(".intel_syntax noprefix;.byte 0x55,0x8b,0xec,0x81,0xc4,0x60,0xff,0xff,0xff;"
        "jmp DWORD PTR [routePathContinue];.att_syntax prefix;");
}
NAKED static void routePathHook(void) {
    __asm__ volatile(".intel_syntax noprefix;pushfd;pushad;push eax;call routePathChanged;"
        "add esp,4;popad;popfd;jmp DWORD PTR [routePathTrampolinePtr];.att_syntax prefix;");
}
#include "route_guards.h"
static int route_install(void) {
    if(routeHooked)return 0;
    for(u32 i=0;i<sizeof(routeGuards)/sizeof(routeGuards[0]);++i)
        if(!matches(game+routeGuards[i].rva,routeGuards[i].bytes,8))return -1;
    u8 *open=game+0x2a0160,*path=game+0x2a339c,*mouse=game+0x2a300c;
    const u8 openBytes[]={0x55,0x8b,0xec,0xb9,0x41,0,0,0};
    const u8 pathBytes[]={0x55,0x8b,0xec,0x81,0xc4,0x60,0xff,0xff,0xff};
    const u8 mouseBytes[]={0x55,0x8b,0xec,0x83,0xc4,0xec};
    if(!matches(open,openBytes,8)||!matches(path,pathBytes,9)||!matches(mouse,mouseBytes,6))return -1;
    routeOpenContinue=open+8;routeOpenTrampolinePtr=routeOpenTrampoline;
    routePathContinue=path+9;routePathTrampolinePtr=routePathTrampoline;
    if(!installJump(open,routeOpenHook,8))return -1;
    if(!installJump(path,routePathHook,9)) {replaceCode(open,openBytes,8);return -1;}
    routeMouseContinue=mouse+6;routeMouseTrampolinePtr=routeMouseTrampoline;
    if(!installJump(mouse,routeMouseHook,6)) {
        replaceCode(path,pathBytes,9);replaceCode(open,openBytes,8);return -1;
    }
    routeHooked=1;return 0;
}
int FHD_RoutePrepare(void) {
    routePending=routeDisplayed=routeSession=0;routeLabel=routeDeadlineLabel=routeMarker=0;
    routeSummary.byteLength=routeDetails.byteLength=routeDeadline.byteLength=0;
    routeSummary.chars[0]=routeDetails.chars[0]=routeDeadline.chars[0]=0;routeDeadlineDays=0;
    if(!enabled)return -1;
    int kind=FHD_OfferKind();u8 *target=(u8 *)FHD_OfferTarget();
    if(kind<0||!target)return -4;
    routePlanet=(kind==0||kind==2)?target:0;
    routeGoal=routePlanet?*(u8 **)(target+0x18):(kind==3?target:*(u8 **)(target+0x24));
    routePlayer=route_player();if(!routePlayer||!routeGoal)return -4;
    routeOrigin=*(u8 **)(routePlayer+0x24);if(!routeOrigin)return -4;
    if(routePlanet&&routePlanet[0x15c])return -7;
    int status=route_install();if(status)return status;
    int speed=route_call(0x32c8dc,routePlayer,0,0);
    if(speed<=0)return -2;
    u8 *tank=(u8 *)route_call(0x30e5fc,routePlayer,0,0);
    u8 *engine=(u8 *)route_call(0x30e618,routePlayer,0,0);
    if(!tank||!engine||!(route_call(0x30e764,routePlayer,tank,0)&255)||
       !(route_call(0x30e764,routePlayer,engine,0)&255))return -2;
    routePlan.engine=route_call(0x30f230,routePlayer,0,0);
    routePlan.capacity=tank[0x68];
    routePlan.bonus=route_call(0x32d804,routePlayer,(ptr)1,0);
    int fuel=*(int *)(tank+0x64);if(fuel<0)fuel=0;
    if(fuel>routePlan.capacity)routePlan.capacity=fuel;
    routePlan.regen=route_fuel_regeneration();routePlan.accelerator=route_hyper_accelerator();
    u8 *galaxy=*(u8 **)(game+0x48c288);if(!galaxy)return -4;
    /* Embedded TfGov.QuestOffer.DeadlineTurn; use the same difference as
       the game's <Day> token, including easy/hard offer negotiations. */
    routeDeadlineDays=*(int *)(government+0xf8)-*(int *)(galaxy+0x4c);
    if(routeDeadlineDays<0)routeDeadlineDays=0;
    u8 *stars=*(u8 **)(galaxy+0x2c);if(!stars)return -4;
    int total=*(int *)(stars+8);u8 **items=*(u8 ***)(stars+4);
    if(total<1||total>RP_STARS||!items)return -6;
    routePlan.count=0;int start=-1,goal=-1;
    for(int i=0;i<total;++i) {
        u8 *star=items[i];if(!star)continue;
        if(star!=routeOrigin&&!(route_call(0x461934,star,0,0)&255))continue;
        int n=routePlan.count++;
        routeStars[n]=star;routePlan.nodes[n].x=*(float *)(star+0x14);
        routePlan.nodes[n].y=*(float *)(star+0x18);
        routePlan.nodes[n].recharge=route_first_refuel(star,routePlayer)!=0;
        if(star==routeOrigin)start=n;
        if(star==routeGoal)goal=n;
    }
    if(start<0||goal<0)return -5;
    status=rp_plan(&routePlan,start,goal,fuel);if(status)return status;
    status=route_estimate(speed);if(status)return status;
    route_build_text(speed);routePending=1;return 0;
}
int FHD_RouteText(void) {return (int)routeSummary.chars;}
int FHD_RouteDeadlineText(void) {return (int)routeDeadline.chars;}
int FHD_RouteTarget(void) {return routePending?(int)routeGoal:0;}
int FHD_RouteDetails(void) {return (int)routeDetails.chars;}
int FHD_RouteDays(void) {return routeDays;}
int FHD_RouteJumps(void) {return routePlan.hops;}
int FHD_RouteRefuels(void) {return routePlan.refuels;}
int FHD_RouteCancel(void) {
    routePending=routeSession=0;routePathChanged(0);routeLabel=routeDeadlineLabel=routeMarker=0;return 0;
}
int FHD_RouteClear(void) {
    routePending=0;
    if(!routeSession)return 0;
    routeSession=0;
    u8 *screen=*(u8 **)(game+0x48bf14);
    routePathChanged(screen);
    if(screen&&route_player()==routePlayer) {
        u8 *list=*(u8 **)(screen+0x104);
        if(list)route_call3(*(ptr *)(*(u8 **)list+8),(u32)list,0,0);
        *(u8 **)(screen+0x100)=*(u8 **)(routePlayer+0x24);
        route_call(0x2a339c,screen,0,0);
        u8 *button=*(u8 **)(screen+0x11c);
        if(button)route_call(0xa1b30,button,(ptr)1,0);
    }
    return 0;
}
