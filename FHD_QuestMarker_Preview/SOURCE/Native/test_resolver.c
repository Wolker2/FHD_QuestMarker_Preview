/* Tests the same resolver against loaded PE32 buffers. No Windows code is run.
   The fixture addresses fit PE32, including on a 64-bit Linux test host. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef int i32;
#include "game_resolver.h"

int main(int argc,char **argv) {
    if(argc!=2)return 1;
    FILE *f=fopen(argv[1],"rb");if(!f)return 2;
    u32 header[4],expected[GS_Count];
    if(fread(header,4,4,f)!=4||fread(expected,4,GS_Count,f)!=GS_Count)return 3;
    if(header[2]!=GS_Count)return 4;
    u8 *image=mmap((void *)(unsigned long)header[3],header[1],PROT_READ|PROT_WRITE,
        MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0);
    if(image==MAP_FAILED)return 5;
    if(fread(image,1,header[1],f)!=header[1])return 6;
    fclose(f);
    for(int i=0;i<GS_Count;++i)gameSymbols[i]=(u8 *)(unsigned long)(0x55aa0000+i);
    int result=game_resolve(image,gameSymbols);
    if(result!=(int)header[0]) {fprintf(stderr,"Unexpected resolve result %d for %s\n",result,argv[1]);return 7;}
    for(int i=0;i<GS_Count;++i) {
        unsigned long wanted=result?expected[i]:0x55aa0000u+(u32)i;
        if((unsigned long)gameSymbols[i]!=wanted) {
            fprintf(stderr,"Wrong symbol %d: %lx expected %lx\n",i,(unsigned long)gameSymbols[i],wanted);return 8;
        }
    }
    munmap(image,header[1]);printf("PASS: %s\n",argv[1]);return 0;
}
