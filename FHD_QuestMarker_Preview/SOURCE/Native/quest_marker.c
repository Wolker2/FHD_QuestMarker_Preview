/* Space Rangers HD 2.1.2500 (user-supplied Rangers.exe).
   Loaded by the game's native ScriptLibs loader, without XenoNativeLoader.
   Exact binary layout: sha256 83300344af802bc51e64389c58f047e5afdf195c133048098be3881fae29ed98.
   Guarded code sites: government choice reset/offer and message right-click callback. */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef int i32;
typedef void *ptr;
#define STDCALL __attribute__((stdcall))
#define NAKED __attribute__((naked))

typedef i32 (STDCALL *Protect)(ptr,ptr *,u32 *,u32,u32 *);
typedef i32 (STDCALL *Flush)(ptr,ptr,u32);
typedef i32 (STDCALL *PinModule)(u32,const u16 *,ptr *);

u8 *game;
ptr originalCallback;
ptr getByNameFn,addChoiceFn,executePressFn;
ptr clearTrampolinePtr,offerTrampolinePtr,easyTrampolinePtr,hardTrampolinePtr;
ptr clearContinue,offerContinue,easyContinue,hardContinue;
static Protect protectMemory;
static Flush flushCache;
static int enabled;
static volatile u32 selectedTarget;
static volatile i32 selectedKind = -1;
static volatile u32 offerVisible;
static u8 *government;
static const struct {u32 byteLength;u16 chars[21];} buttonName={40,
    {'F','H','D','Q','u','e','s','t','R','e','t','u','r','n','B','u','t','t','o','n',0}};

/* Delphi WideString/BSTR literal: dark-blue real dialogue item, matching the user's mock-up. */
static const struct {u32 byteLength;u16 chars[41];} showChoiceText={80,
    {'<','c','o','l','o','r','=','0',',','0',',','1','3','9','>',
     0x041f,0x043e,0x043a,0x0430,0x0437,0x0430,0x0442,0x044c,' ',0x043d,0x0430,' ',
     0x043a,0x0430,0x0440,0x0442,0x0435,'<','/','c','o','l','o','r','>',0}};

static int asciiEqual(const char *a,const char *b) {
    if(!a||!b)return 0;
    while(*a&&*b)if(*a++!=*b++)return 0;
    return *a==*b;
}
NAKED static ptr pebAddress(void) {__asm__ volatile("movl %fs:0x30,%eax;ret");}
static ptr findModule(const char *match) {
    u8 *peb=(u8 *)pebAddress();if(!peb)return 0;
    u8 *ldr=*(u8 **)(peb+0x0c);if(!ldr)return 0;
    u8 *head=ldr+0x14,*link=*(u8 **)head;
    for(int i=0;link&&link!=head&&i<32;++i) {
        u8 *entry=link-8,*base=*(u8 **)(entry+0x18);
        const u16 *name=*(const u16 **)(entry+0x30);
        if(base&&name) {
            int j=0;
            for(;match[j];++j) {
                u16 c=name[j];if(c>='A'&&c<='Z')c+=32;
                if(c!=(u8)match[j])break;
            }
            if(!match[j]&&!name[j])return base;
        }
        link=*(u8 **)link;
    }
    return 0;
}
static ptr findExport(ptr module,const char *wanted) {
    u8 *base=(u8 *)module;if(!base||*(u16 *)base!=0x5a4d)return 0;
    u8 *nt=base+*(u32 *)(base+0x3c);
    if(*(u32 *)nt!=0x4550||*(u16 *)(nt+24)!=0x10b)return 0;
    u8 *opt=nt+24;u32 rva=*(u32 *)(opt+96),len=*(u32 *)(opt+100);
    if(!rva)return 0;
    u8 *exp=base+rva,*p=base;
    u32 count=*(u32 *)(exp+20),n=*(u32 *)(exp+24);
    u32 *functions=(u32 *)(p+*(u32 *)(exp+28));
    u32 *names=(u32 *)(p+*(u32 *)(exp+32));
    u16 *ordinals=(u16 *)(p+*(u32 *)(exp+36));
    for(u32 i=0;i<n;++i)if(asciiEqual((char *)(p+names[i]),wanted)) {
        u16 ord=ordinals[i];if(ord>=count)return 0;
        u32 found=functions[ord];return found>=rva&&found<rva+len?0:p+found;
    }
    return 0;
}
static int replacePointer(void *location,u32 newValue) {
    ptr page=location;u32 bytes=4,old=0,ignored=0;
    if(!protectMemory||protectMemory((ptr)-1,&page,&bytes,0x40,&old)<0)return 0;
    *(u32 *)location=newValue;
    flushCache((ptr)-1,location,4);
    protectMemory((ptr)-1,&page,&bytes,old,&ignored);
    return 1;
}
static int replaceCode(void *location,const u8 *bytes,u32 length) {
    ptr page=location;u32 size=length,old=0,ignored=0;
    if(!protectMemory||protectMemory((ptr)-1,&page,&size,0x40,&old)<0)return 0;
    for(u32 i=0;i<length;++i)((u8 *)location)[i]=bytes[i];
    flushCache((ptr)-1,location,length);
    protectMemory((ptr)-1,&page,&size,old,&ignored);
    return 1;
}
/* Native bridge used only by the real government dialogue choice.
   The hidden GraphButton owns the RScript OnPressCode; calling its native
   ExecuteOnPressCode queues that script through the game's normal UI path. */
__attribute__((used)) void clearOfferState(void) {
    offerVisible=0; government=0;
}
__attribute__((used)) void invokeOfferMapChoice(u8 *gov) {
    if(!enabled||!gov)return;
    register ptr obj __asm__("eax")=gov;
    register ptr name __asm__("edx")=(ptr)buttonName.chars;
    __asm__ volatile("call *%2":"+a"(obj),"+d"(name):"m"(getByNameFn):"ecx","memory","cc");
    if(!obj)return;
    register ptr control __asm__("eax")=obj;
    __asm__ volatile("call *%1":"+a"(control):"m"(executePressFn):"ecx","edx","memory","cc");
}
/* TDialogChoiceEventGI: EAX=Self (government), EDX=Value. */
NAKED static void offerMapChoice(void) {
    __asm__ volatile(
        ".intel_syntax noprefix;"
        "push eax;push eax;call invokeOfferMapChoice;add esp,4;pop eax;ret;"
        ".att_syntax prefix;"
    );
}
__attribute__((used)) void appendOfferChoice(u8 *gov) {
    if(!enabled||!gov||offerVisible)return;
    offerVisible=1; government=gov;
    register ptr self __asm__("eax")=gov;
    register ptr text __asm__("edx")=(ptr)showChoiceText.chars;
    register u32 value __asm__("ecx")=0;
    ptr callback=(ptr)offerMapChoice;
    __asm__ volatile(
        "pushl %4;pushl %3;call *%5"
        : "+a"(self), "+d"(text), "+c"(value)
        : "r"(callback), "r"(gov), "m"(addChoiceFn)
        : "memory","cc");
}
NAKED static void clearTrampoline(void) {
    __asm__ volatile(
        ".intel_syntax noprefix;"
        ".byte 0x55,0x8b,0xec,0x83,0xc4,0xf4;"
        "jmp DWORD PTR [clearContinue];"
        ".att_syntax prefix;"
    );
}
NAKED static void offerTrampoline(void) {
    __asm__ volatile(
        ".intel_syntax noprefix;"
        ".byte 0x55,0x8b,0xec,0x33,0xc9;"
        "jmp DWORD PTR [offerContinue];"
        ".att_syntax prefix;"
    );
}
NAKED static void easyTrampoline(void) {
    __asm__ volatile(
        ".intel_syntax noprefix;"
        ".byte 0x55,0x8b,0xec,0xb9,0x04,0,0,0;"
        "jmp DWORD PTR [easyContinue];"
        ".att_syntax prefix;"
    );
}
NAKED static void hardTrampoline(void) {
    __asm__ volatile(
        ".intel_syntax noprefix;"
        ".byte 0x55,0x8b,0xec,0xb9,0x04,0,0,0;"
        "jmp DWORD PTR [hardContinue];"
        ".att_syntax prefix;"
    );
}
NAKED static void clearHook(void) {
    __asm__ volatile(
        ".intel_syntax noprefix;"
        "push eax;call clearOfferState;pop eax;"
        "jmp DWORD PTR [clearTrampolinePtr];"
        ".att_syntax prefix;"
    );
}
NAKED static void offerHook(void) {
    __asm__ volatile(
        ".intel_syntax noprefix;"
        "push ebx;mov ebx,eax;call DWORD PTR [offerTrampolinePtr];"
        "push ebx;call appendOfferChoice;add esp,4;pop ebx;ret;"
        ".att_syntax prefix;"
    );
}
NAKED static void easyHook(void) {
    __asm__ volatile(
        ".intel_syntax noprefix;"
        "push ebx;mov ebx,eax;call DWORD PTR [easyTrampolinePtr];"
        "push ebx;call appendOfferChoice;add esp,4;pop ebx;ret;"
        ".att_syntax prefix;"
    );
}
NAKED static void hardHook(void) {
    __asm__ volatile(
        ".intel_syntax noprefix;"
        "push ebx;mov ebx,eax;call DWORD PTR [hardTrampolinePtr];"
        "push ebx;call appendOfferChoice;add esp,4;pop ebx;ret;"
        ".att_syntax prefix;"
    );
}
static int matches(const u8 *a,const u8 *b,u32 length) {
    for(u32 i=0;i<length;++i)if(a[i]!=b[i])return 0;
    return 1;
}
static int installJump(u8 *site,ptr hook,u32 length) {
    u8 bytes[16]={0xe9,0,0,0,0,0x90,0x90,0x90,0x90,0x90,0x90,0x90,0x90,0x90,0x90,0x90};
    if(length<5||length>sizeof(bytes))return 0;
    *(i32 *)(bytes+1)=(i32)((u8 *)hook-(site+5));
    return replaceCode(site,bytes,length);
}
static u32 wideLength(const u16 *s,u32 max) {
    if(!s)return 0;
    for(u32 i=0;i<max;++i)if(!s[i])return i;
    return 0;
}
static int containsWide(const u16 *haystack,const u16 *needle) {
    u32 n=wideLength(needle,4096),h=wideLength(haystack,16384);
    if(n<8||!h||n>h)return 0;
    for(u32 i=0;i+n<=h;++i) {
        u32 j=0;for(;j<n&&haystack[i+j]==needle[j];++j){}
        if(j==n)return 1;
    }
    return 0;
}
/* Delphi TMessagePlayer: Kind at +0x10, Text +0x20.
   Delphi TList: Items +0x04, Count +0x08. TRanger.Quests +0x520.
   TQuest: Type +0x00, ObjectiveTarget +0x10, Description +0x18. */
__attribute__((used)) int captureQuest(u8 *sender) {
    selectedKind=-1;selectedTarget=0;
    if(!enabled||!sender)return 0;
    u8 *message=*(u8 **)(sender+0x8c);
    if(!message||message[0x10]!=3)return 0;
    typedef ptr (*GetPlayer)(void);
    u8 *player=(u8 *)((GetPlayer)(game+0x38c078))();
    if(!player)return 0;
    u8 *list=*(u8 **)(player+0x520);
    if(!list)return 0;
    u32 count=*(u32 *)(list+8);
    u8 **entries=*(u8 ***)(list+4);
    if(!entries||count>256)return 0;
    const u16 *messageText=*(const u16 **)(message+0x20);
    for(u32 i=0;i<count;++i) {
        u8 *quest=entries[i];if(!quest)continue;
        const u16 *description=*(const u16 **)(quest+0x18);
        if(!containsWide(messageText,description))continue;
        u32 target=*(u32 *)(quest+0x10);
        i32 kind=quest[0];
        if(target&&kind>=0&&kind<=4) {
            selectedKind=kind;selectedTarget=target;
            return 1; /* Let the panel's OnMouseRightClick run. */
        }
        break;
    }
    return 0;
}
/* Delphi register callback: EAX=panel, EDX=button, ECX=key state,
   [ESP+4]=point pointer; callee removes 4 bytes. Preserve all for fallback. */
NAKED static void questRightClick(void) {
    __asm__ volatile(
        ".intel_syntax noprefix;"
        "push eax;push edx;push ecx;push edx;"
        "call captureQuest;add esp,4;"
        "test eax,eax;pop ecx;pop edx;pop eax;"
        "jnz 1f;"
        "jmp DWORD PTR [originalCallback];"
        "1:ret 4;"
        ".att_syntax prefix;"
    );
}

int FHD_GetKind(void) {return selectedKind;}
int FHD_GetTarget(void) {return (int)selectedTarget;}
int FHD_Reset(void) {selectedKind=-1;selectedTarget=0;return 0;}
int FHD_OfferKind(void) {
    if(!offerVisible||!government)return -1;
    i32 kind=government[0xf0];
    return (kind>=0&&kind<=4)?kind:-1;
}
int FHD_OfferTarget(void) {
    return (offerVisible&&government)?*(int *)(government+0x100):0;
}

/* Called by BV.OnStart and BV.OnLoad through the game's ScriptLibs API. */
u32 FHDQuest_Init(void) {
    if(enabled)return 0;
    u8 *peb=(u8 *)pebAddress();
    if(!peb)return 1;
    game=*(u8 **)(peb+8);
    if(!game||*(u16 *)game!=0x5a4d)return 2;
    u8 *nt=game+*(u32 *)(game+0x3c);
    if(*(u32 *)nt!=0x4550||*(u16 *)(nt+24)!=0x10b)return 2;
    if(*(u32 *)(nt+24+56)!=0x4d1000)return 3;
    if(*(u32 *)(nt+8)!=0x68eccc46)return 3; /* PE timestamp of target EXE */
    const u8 expected[] = {0xc7,0x80,0xb8,0,0,0};
    u8 *site=game+0x3a3cde;
    for(u32 i=0;i<sizeof(expected);++i)if(site[i]!=expected[i])return 4;
    if(*(u32 *)(site+6)!=(u32)(game+0x3a4810))return 4;
    if(*(u32 *)(game+0x12bba2)!=0x00000520)return 4;
    const u8 clearBytes[]={0x55,0x8b,0xec,0x83,0xc4,0xf4};
    const u8 offerBytes[]={0x55,0x8b,0xec,0x33,0xc9};
    const u8 negotiateBytes[]={0x55,0x8b,0xec,0xb9,0x04,0,0,0};
    u8 *clearSite=game+0x1276ec,*offerSite=game+0x129e34;
    u8 *easySite=game+0x12b518,*hardSite=game+0x12b810;
    if(!matches(clearSite,clearBytes,6)||!matches(offerSite,offerBytes,5)||
       !matches(easySite,negotiateBytes,8)||!matches(hardSite,negotiateBytes,8))return 4;
    ptr ntdll=findModule("ntdll.dll");
    protectMemory=(Protect)findExport(ntdll,"NtProtectVirtualMemory");
    flushCache=(Flush)findExport(ntdll,"NtFlushInstructionCache");
    if(!protectMemory||!flushCache)return 5;
    ptr kernelbase=findModule("kernelbase.dll");
    ptr kernel32=findModule("kernel32.dll");
    PinModule pin=(PinModule)findExport(kernelbase,"GetModuleHandleExW");
    if(!pin)pin=(PinModule)findExport(kernel32,"GetModuleHandleExW");
    ptr pinned=0;
    /* The game frees its ScriptLibs cache when resetting a party. Hook
       callbacks must remain mapped until Rangers.exe exits. */
    if(!pin||!pin(1|4,(const u16 *)FHDQuest_Init,&pinned)||!pinned)return 7;
    originalCallback=game+0x3a4810;
    getByNameFn=game+0xcefc8;
    addChoiceFn=game+0x127768;
    executePressFn=game+0xa2844;
    clearContinue=clearSite+6;offerContinue=offerSite+5;
    easyContinue=easySite+8;hardContinue=hardSite+8;
    clearTrampolinePtr=clearTrampoline;offerTrampolinePtr=offerTrampoline;
    easyTrampolinePtr=easyTrampoline;hardTrampolinePtr=hardTrampoline;
    if(!installJump(clearSite,clearHook,6))return 6;
    if(!installJump(offerSite,offerHook,5)) {
        replaceCode(clearSite,clearBytes,6);return 6;
    }
    if(!installJump(easySite,easyHook,8)) {
        replaceCode(offerSite,offerBytes,5);replaceCode(clearSite,clearBytes,6);return 6;
    }
    if(!installJump(hardSite,hardHook,8)) {
        replaceCode(easySite,negotiateBytes,8);replaceCode(offerSite,offerBytes,5);
        replaceCode(clearSite,clearBytes,6);return 6;
    }
    if(!replacePointer(site+6,(u32)questRightClick)) {
        replaceCode(hardSite,negotiateBytes,8);replaceCode(easySite,negotiateBytes,8);
        replaceCode(offerSite,offerBytes,5);replaceCode(clearSite,clearBytes,6);
        return 6;
    }
    enabled=1;
    return 0;
}
#include "quest_route.h"
int STDCALL DllMain(ptr module,u32 reason,ptr reserved) {
    (void)module;(void)reason;(void)reserved;return 1;
}
