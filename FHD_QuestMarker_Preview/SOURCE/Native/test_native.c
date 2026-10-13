/* Linux/i386 ABI test with synthetic game objects. Does not run Rangers.exe.
   Build/run commands are in test_native.sh. Mocks have Delphi register ABI;
   CanBoostArtefact additionally consumes its fourth stack argument. */
#include "quest_marker.c"
#define REG __attribute__((regparm(3)))
static u8 fakegame[0x4d1000] __attribute__((aligned(4096)));
static u8 player[0xe00],gov[0x108],galaxy[0x80],stars[3][0x114],planets[3][0x168];
static u8 tank[0x70],engine[0x70],screen[0x148],label[0x180],deadlineLabel[0x180],marker[0x120],jumpButton[0x200],frame[0x120];
typedef struct {ptr vmt;ptr *items;int count,capacity;} List;
static ptr starItems[3],planetItems[3][1],pathItems[256],listVmt[3];
static List starList,planetLists[3],pathList;
static volatile int redraws,labelHasText,deadlineActive,highlighted,textsCleared;
static volatile int deadlineHasText,markerActive;
static int fuelArtefacts;
static volatile int mouseCalls;
static void fail(int line) {__asm__ volatile("int $0x80"::"a"(1),"b"(line?line%250:251));__builtin_unreachable();}
#define CHECK(x) do {if(!(x))fail(__LINE__);}while(0)
static void REG mockClear(List *list,u32 ignored,u32 ignored2) {
    (void)ignored;(void)ignored2;list->count=0;
}
static u32 REG mockAdd(List *list,ptr value,u32 ignored) {
    (void)ignored;CHECK(list->count<list->capacity);int n=list->count++;list->items[n]=value;return n;
}
static u32 REG mockPlayer(u32 a,u32 d,u32 c) {(void)a;(void)d;(void)c;return (u32)player;}
static u32 REG mockSpeed(u32 a,u32 d,u32 c) {(void)a;(void)d;(void)c;return 200;}
static u32 REG mockRange(u32 a,u32 d,u32 c) {(void)a;(void)d;(void)c;return 10;}
static u32 REG mockTank(u32 a,u32 d,u32 c) {(void)a;(void)d;(void)c;return (u32)tank;}
static u32 REG mockEngine(u32 a,u32 d,u32 c) {(void)a;(void)d;(void)c;return (u32)engine;}
static u32 REG mockTrue(u32 a,u32 d,u32 c) {(void)a;(void)d;(void)c;return 1;}
static u32 REG mockZero(u32 a,u32 d,u32 c) {(void)a;(void)d;(void)c;return 0;}
static u32 REG mockArtefacts(u32 a,u32 d,u32 c) {(void)a;(void)c;return d==11?fuelArtefacts:0;}
static u32 REG mockJumpDays(u32 a,u32 d,u32 c) {(void)a;(void)d;(void)c;return 2;}
static u32 REG STDCALL mockBoost(u32 a,u32 d,u32 c,int flag) {
    (void)a;(void)c;CHECK((d==34||d==11)&&flag==0);return 0;
}
static void REG mockPlanetPoint(u8 *planet,RoutePoint *out,u32 c) {
    (void)c;out->x=*(double *)(planet+0x28)+*(double *)(planet+0x20);out->y=0;
}
static void REG mockDeparture(u8 *proxy,u8 *dest,RoutePoint *out) {
    CHECK(proxy!=player&&*(u8 **)(proxy+0x24)!=dest);out->x=1000;out->y=0;
}
static void REG mockArrival(u8 *proxy,u8 *dest,RoutePoint *out) {
    CHECK(proxy!=player&&*(u8 **)(proxy+0x24)!=dest);out->x=-1000;out->y=0;
}
static u32 REG mockName(u32 a,const u16 *name,u32 c) {
    (void)a;(void)c;
    if(name[8]=='M') {CHECK(*(u32 *)(name-2)==32);return (u32)marker;}
    if(name[13]=='F') {CHECK(*(u32 *)(name-2)==36);return (u32)frame;}
    if(name[13]=='I') {CHECK(*(u32 *)(name-2)==34);return (u32)label;}
    CHECK(name[13]=='D'&&*(u32 *)(name-2)==42);return (u32)deadlineLabel;
}
static void REG mockText(u8 *object,const u16 *text,u32 c) {
    (void)c;CHECK(object==label||object==deadlineLabel);
    if(object==label)labelHasText=text&&text[0];else deadlineHasText=text&&text[0];
    if(!text)++textsCleared;
    if(text)CHECK(*(u32 *)(text-2)>0&&*(u32 *)(text-2)<2048);
}
static void REG mockActive(u8 *object,u32 active,u32 c) {
    (void)c;CHECK(object==deadlineLabel||object==marker);
    if(object==marker)markerActive=active!=0;else deadlineActive=active!=0;
}
static void REG mockDisabled(u8 *object,u32 disabled,u32 c) {
    (void)c;CHECK(object==jumpButton);object[0x123]=disabled!=0;
}
static void REG mockPath(u8 *object,u32 d,u32 c) {
    (void)d;(void)c;CHECK(object==screen);++redraws;routePathChanged(object);
}
static void REG mockHighlight(u8 *object,u8 *star,u32 c) {
    (void)c;CHECK(object==screen&&star==stars[2]);++highlighted;
}
static void stub(u32 rva,ptr fn) {
    /* push absolute address; ret: preserves the three argument registers. */
    fakegame[rva]=0x68;*(u32 *)(fakegame+rva+1)=(u32)fn;fakegame[rva+5]=0xc3;
}
static void REG STDCALL mockMouseUp(u8 *object,u32 sender,u32 state,const int *point) {
    CHECK(object==screen&&sender==123&&state==456&&point[0]==99);++mouseCalls;
}
static void checkPanelClick(void) {
    frame[0x41]=1;int *bounds=(int *)(frame+0x60);
    bounds[0]=100;bounds[1]=200;bounds[2]=500;bounds[3]=240;
    int point[2]={100,200};
    CHECK(routePanelClick(screen,point));
    routeMouseTrampolinePtr=mockMouseUp;
    u32 a=(u32)screen,d=123,c=456;ptr fn=routeMouseHook;const int *pointAddress=point;
    __asm__ volatile("pushl %4;call *%3":"+a"(a),"+d"(d),"+c"(c):"r"(fn),"m"(pointAddress):
        "memory","cc","st","st(1)","st(2)","st(3)","st(4)","st(5)","st(6)","st(7)");
    CHECK(!mouseCalls&&a==(u32)screen&&d==123&&c==456);
    point[0]=99;CHECK(!routePanelClick(screen,point));
    a=(u32)screen;d=123;c=456;
    __asm__ volatile("pushl %4;call *%3":"+a"(a),"+d"(d),"+c"(c):"r"(fn),"m"(pointAddress):
        "memory","cc","st","st(1)","st(2)","st(3)","st(4)","st(5)","st(6)","st(7)");
    CHECK(mouseCalls==1);
    frame[0x41]=0;point[0]=100;CHECK(!routePanelClick(screen,point));
}
static void init(void) {
    game=fakegame;enabled=offerVisible=routeHooked=1;government=gov;
    __asm__ volatile("int $0x80"::"a"(125),"b"(fakegame),"c"(sizeof(fakegame)),"d"(7):"memory");
    stub(0x38c078,mockPlayer);stub(0x32c8dc,mockSpeed);stub(0x30f230,mockRange);
    stub(0x30e5fc,mockTank);stub(0x30e618,mockEngine);stub(0x30e764,mockTrue);
    stub(0x37d484,mockTrue);stub(0x461934,mockTrue);stub(0x32d804,mockZero);
    stub(0x325cb8,mockBoost);stub(0x325a74,mockArtefacts);stub(0x31c634,mockJumpDays);
    stub(0x379d1c,mockPlanetPoint);stub(0x31c4b4,mockDeparture);stub(0x31c590,mockArrival);
    stub(0xcefc8,mockName);stub(0x90104,mockText);stub(0xc9eac,mockActive);
    stub(0x161c0,mockAdd);stub(0x2a339c,mockPath);stub(0x2a5078,mockHighlight);
    stub(0xa1b30,mockDisabled);
    *(ptr *)(game+0x48c288)=galaxy;*(ptr *)(game+0x48bf14)=screen;
    starList=(List){0,starItems,3,3};*(ptr *)(galaxy+0x2c)=&starList;
    listVmt[2]=mockClear;pathList=(List){listVmt,pathItems,0,256};
    *(ptr *)(screen+0x104)=&pathList;*(ptr *)(screen+0x11c)=jumpButton;screen[0xd8]=2;
    for(int i=0;i<3;++i) {
        starItems[i]=stars[i];planetItems[i][0]=planets[i];
        planetLists[i]=(List){0,planetItems[i],1,1};
        *(ptr *)(stars[i]+0x24)=&planetLists[i];*(float *)(stars[i]+0x14)=i*9;
        *(ptr *)(planets[i]+0x18)=stars[i];
        *(double *)(planets[i]+0x28)=0;
    }
    *(ptr *)(player+0x24)=stars[0];*(ptr *)(player+0x1c)=planets[0];
    *(ptr *)(gov+0x100)=planets[2];gov[0xf0]=0;tank[0x68]=10;*(int *)(tank+0x64)=10;
    *(int *)(galaxy+0x4c)=1000;*(int *)(gov+0xf8)=1120;
    *(int *)(game+0x489e28)=1;*(int *)(game+0x489e98)=1;
}
static void expectDeadline(const u16 *expected) {
    const u16 *actual=(const u16 *)FHD_RouteDeadlineText();int n=0;
    while(expected[n]) {CHECK(actual[n]==expected[n]);++n;}
    CHECK(actual[n]==0&&*(u32 *)(actual-2)==(u32)n*2);
}
static void checkDeadlines(void) {
    /* Actual offer deadlines after easy/hard negotiation; not route ETA. */
    *(int *)(gov+0xf8)=1180;CHECK(FHD_RoutePrepare()==0);
    expectDeadline(u"Срок: 180 дн.");FHD_RouteCancel();
    *(int *)(gov+0xf8)=1060;CHECK(FHD_RoutePrepare()==0);
    expectDeadline(u"Срок: 60 дн.");FHD_RouteCancel();
    *(int *)(gov+0xf8)=995;CHECK(FHD_RoutePrepare()==0);
    expectDeadline(u"Срок: 0 дн.");FHD_RouteCancel();
    *(int *)(gov+0xf8)=1120;*(int *)(galaxy+0x4c)=1007;
    CHECK(FHD_RoutePrepare()==0);expectDeadline(u"Срок: 113 дн.");FHD_RouteCancel();
    *(int *)(galaxy+0x4c)=1000;
    /* Clearing an applied route also removes its animated endpoint. */
    CHECK(FHD_RoutePrepare()==0);routeApply(screen);
    CHECK(markerActive&&deadlineActive&&deadlineHasText);
    FHD_RouteClear();
    CHECK(!markerActive&&!deadlineActive&&!deadlineHasText&&!labelHasText);
    CHECK(!routeSession&&!routePending&&!pathList.count);
    CHECK((const u8 *)FHD_RouteTarget()==0);
    /* Closing and reopening does not inherit the old endpoint or deadline. */
    CHECK(FHD_RoutePrepare()==0);routeApply(screen);CHECK(markerActive);
    FHD_RouteCancel();CHECK(!markerActive&&!deadlineActive&&!routePending&&!routeSession);
    int n=redraws;routeApply(screen);CHECK(redraws==n&&!markerActive);
}
static void run(void) {
    init();checkPanelClick();CHECK(FHD_RoutePrepare()==0);
    CHECK(routePlan.hops==2&&routePlan.refuels==1&&routeDays==24);
    expectDeadline(u"Срок: 120 дн.");
    CHECK((u8 *)FHD_RouteTarget()==stars[2]);
    CHECK(routeDays==routeJumpDays+routeSystemDays+routeDockDays);
    CHECK(*(u8 **)(player+0x24)==stars[0]&&*(int *)(tank+0x64)==10);
    CHECK(*(double *)(planets[0]+0x20)==0&&*(double *)(planets[2]+0x20)==0);
    routeApply(screen);
    CHECK(!routePending&&routeDisplayed&&routeSession&&labelHasText&&deadlineActive&&deadlineHasText&&markerActive);
    CHECK(*(u8 **)(screen+0x100)==stars[1]&&pathList.count==1&&pathList.items[0]==stars[2]);
    CHECK(jumpButton[0x123]==0&&highlighted==1);
    CHECK(routeLabel==label&&routeDeadlineLabel==deadlineLabel&&routeMarker==marker);
    routePathChanged(screen);
    CHECK(!routeDisplayed);
    CHECK(textsCleared==2);
    CHECK(!labelHasText);
    CHECK(!deadlineActive&&!deadlineHasText&&!markerActive);
    CHECK(routeSession);
    FHD_RouteClear();CHECK(pathList.count==0&&*(u8 **)(screen+0x100)==stars[0]&&jumpButton[0x123]);
    int n=redraws;routeApply(screen);CHECK(redraws==n);
    checkDeadlines();
    *(ptr *)(gov+0x100)=planets[0];CHECK(FHD_RoutePrepare()==0&&routePlan.hops==0&&routeDays==0);
    FHD_RouteCancel();CHECK(!routePending&&!routeSession);
    *(ptr *)(gov+0x100)=planets[2];fuelArtefacts=1;
    CHECK(FHD_RoutePrepare()==0&&routePlan.hops==2&&routePlan.refuels==0&&routeDays==22);
    CHECK(*(int *)(tank+0x64)==10);
    FHD_RouteCancel();fuelArtefacts=0;
    /* Moving-planet prediction must be isolated from the real orbit. */
    *(double *)(planets[2]+0x20)=2;*(double *)(planets[2]+0x40)=3;
    RoutePoint position;route_planet_point(planets[2],4,&position);
    CHECK(position.x==14&&*(double *)(planets[2]+0x20)==2);
    /* Ship objectives use a system ETA, with no fictional final landing. */
    u8 ship[0x28]={0};*(ptr *)(ship+0x24)=stars[2];gov[0xf0]=1;*(ptr *)(gov+0x100)=ship;
    CHECK(FHD_RoutePrepare()==0&&!routePlanet&&routeDays==19);
    FHD_RouteCancel();
    planets[2][0x15c]=1;gov[0xf0]=0;*(ptr *)(gov+0x100)=planets[2];
    CHECK(FHD_RoutePrepare()==-7&&!routePending);
}
void _start(void) {
    run();
    const char text[]="PASS: i386 Delphi ABI, native route preparation/application/reset, ETA ledger, same-system goal, moving planet, ship objective, offer deadlines, animated endpoint cleanup and extended-panel click ABI\n";
    __asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(text),"d"(sizeof(text)-1):"memory");
    __asm__ volatile("int $0x80"::"a"(1),"b"(0));__builtin_unreachable();
}
