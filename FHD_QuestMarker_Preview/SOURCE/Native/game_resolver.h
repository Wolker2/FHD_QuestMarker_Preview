/* Resolve an ABI-compatible running image by unique masked instructions.
   Relative call operands and relocated absolute addresses are wildcarded;
   object offsets, opcodes, stack cleanup and constants remain exact. */
#include "game_patterns.h"
typedef struct {u8 *base,*sections;u32 size;u16 count;} GameImage;

static int game_image(GameImage *out,u8 *base) {
    if(!base||*(u16 *)base!=0x5a4d)return 0;
    u32 ntOffset=*(u32 *)(base+0x3c);
    if(ntOffset<64||ntOffset>0x800)return 0;
    u8 *nt=base+ntOffset;
    if(*(u32 *)nt!=0x4550||*(u16 *)(nt+4)!=0x14c)return 0;
    u16 count=*(u16 *)(nt+6),optionalSize=*(u16 *)(nt+20);
    if(!count||count>64||optionalSize<224||optionalSize>512)return 0;
    if(*(u16 *)(nt+24)!=0x10b)return 0;
    u32 sectionOffset=ntOffset+24+optionalSize;
    if(sectionOffset+40*(u32)count>4096)return 0;
    u32 imageSize=*(u32 *)(nt+24+56);
    if(imageSize<4096||imageSize>0x10000000)return 0;
    for(u16 i=0;i<count;++i) {
        u8 *section=base+sectionOffset+40*i;
        u32 rva=*(u32 *)(section+12),size=*(u32 *)(section+8),raw=*(u32 *)(section+16);
        if(raw>size)size=raw;
        if(rva>imageSize||size>imageSize-rva)return 0;
    }
    out->base=base;out->size=imageSize;out->count=count;out->sections=base+sectionOffset;
    return 1;
}
static int game_section_contains(const GameImage *image,const u8 *address,u32 length,u32 flags) {
    unsigned long distance=(unsigned long)address-(unsigned long)image->base;
    if(distance>image->size)return 0;
    u32 offset=(u32)distance;
    if(offset>image->size||length>image->size-offset)return 0;
    for(u16 i=0;i<image->count;++i) {
        const u8 *section=image->sections+40*i;
        u32 rva=*(const u32 *)(section+12),size=*(const u32 *)(section+8),raw=*(const u32 *)(section+16);
        if(raw>size)size=raw;
        if((*(const u32 *)(section+36)&flags)!=flags)continue;
        if(offset>=rva&&offset-rva<=size&&length<=size-(offset-rva))return 1;
    }
    return 0;
}
static int game_pattern_matches(const u8 *at,const GamePattern *pattern) {
    for(u16 i=0;i<pattern->length;++i)
        if(pattern->mask[i]&&at[i]!=pattern->bytes[i])return 0;
    return 1;
}
static u8 *game_find_pattern(const GameImage *image,const GamePattern *pattern) {
    u8 *found=0;
    for(u16 i=0;i<image->count;++i) {
        const u8 *section=image->sections+40*i;
        if((*(const u32 *)(section+36)&0x60000000)!=0x60000000)continue;
        u32 size=*(const u32 *)(section+8),raw=*(const u32 *)(section+16);
        if(raw>size)size=raw;
        if(size<pattern->length)continue;
        u8 *start=image->base+*(const u32 *)(section+12);
        for(u32 j=0;j<=size-pattern->length;++j) {
            const u8 *candidate=start+j;
            if(candidate[pattern->anchor]!=pattern->bytes[pattern->anchor])continue;
            u16 k=1;
            for(;k<pattern->anchorLength;++k)
                if(candidate[pattern->anchor+k]!=pattern->bytes[pattern->anchor+k])break;
            if(k!=pattern->anchorLength||!game_pattern_matches(candidate,pattern))continue;
            if(found)return 0; /* Ambiguity is rejected, never guessed. */
            found=(u8 *)candidate;
        }
    }
    return found;
}
static int game_resolve(u8 *base,u8 **output) {
    GameImage image;
    if(!game_image(&image,base))return 0;
    u8 *locations[GS_Count],*resolved[GS_Count];
    for(u16 i=0;i<GS_Count;++i) {
        const GamePattern *pattern=&gamePatterns[i];
        u8 *at=game_find_pattern(&image,pattern);
        if(!at)return 0;
        locations[i]=at;
        if(pattern->kind==1||pattern->kind==3) {
            resolved[i]=(u8 *)(unsigned long)*(u32 *)(at+pattern->offset);
            if(pattern->kind==3) {
                if(!game_section_contains(&image,resolved[i],4,0x40000000))return 0;
                resolved[i]=(u8 *)(unsigned long)*(u32 *)resolved[i];
            }
            if(!game_section_contains(&image,resolved[i],4,0xc0000000))return 0;
        } else if(pattern->kind==2) {
            u8 *operand=at+pattern->offset;
            resolved[i]=operand+4+*(i32 *)operand;
            if(!game_section_contains(&image,resolved[i],pattern->guardLength,0x60000000))return 0;
            for(u16 j=0;j<pattern->guardLength;++j)
                if(pattern->guardMask[j]&&resolved[i][j]!=pattern->guard[j])return 0;
        } else resolved[i]=at+pattern->offset;
    }
    for(u32 i=0;i<sizeof(gameEdges)/sizeof(gameEdges[0]);++i) {
        u8 *operand=locations[gameEdges[i].source]+gameEdges[i].operand;
        if(operand+4+*(i32 *)operand!=resolved[gameEdges[i].target])return 0;
    }
    if((u8 *)(unsigned long)*(u32 *)(resolved[GS_CallbackStore]+6)!=resolved[GS_MessageRightClick])return 0;
    if(resolved[GS_GalaxyGlobal]!=resolved[GS_GalaxyGlobalCheck]||
       resolved[GS_GalaxyScreenGlobal]!=resolved[GS_GalaxyScreenGlobalCheck]||
       resolved[GS_FuelBaseGlobal]!=resolved[GS_FuelBaseGlobalCheck]||
       resolved[GS_FuelBoostGlobal]!=resolved[GS_FuelBoostGlobalCheck])return 0;
    /* Publish only after the complete code/data/call-graph profile agrees. */
    for(u16 i=0;i<GS_Count;++i)output[i]=resolved[i];
    return 1;
}
