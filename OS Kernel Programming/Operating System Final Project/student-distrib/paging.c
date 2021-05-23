#include "multiboot.h"
#include "x86_desc.h"
#include "lib.h"
#include "i8259.h"
#include "debug.h"
#include "tests.h"
#include "idt.h"
#include "rtc.h"
#include "paging.h"
#include "task.h"

#define NUMBER_OF_PDE_OR_PTE 1024 /*maximum number of page directory entries in one page directory table*/
#define PHYSICAL_ADDR_OF_KERNEL_MEM 0x400000 /*physical memory address of kernel memory*/
#define SETTING_BIT_12_TO_21_OF_PTE 12 /*shift from bit 0 - 9 to bit 12 - 21*/
#define PHYSICAL_ADDR_OF_VIDEO_MEM 0xB8 /*physical memory address of video mem*/
#define CHANG_BIT_1_OF_CR4 0x00000010
#define _128_MB 32
#define _132_MB 34
#define VMEM_ADDR 0xB8000
#define ACTUAL_128MB_PHY_ADDR 0x800000
#define TEMP_VMEM   0x2C00000

/* 
 *  setup_page_directory
 *   DESCRIPTION: Fills up the all 1024 entries for the page directory table.
 *                Currently, only two page directories entries will be present.
 *                PDE (page directory entry) 0 will be present as the page table it points to will point towards video memory
 *                PDE 01 is also present but it's a 4 MB page
 *   INPUTS: NIL
 *   OUTPUTS: All 1024 entries of page directory table filled up
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */

void setup_page_directory()
{
    /*Setup page directory*/
    int i;
    for(i=0; i<NUMBER_OF_PDE_OR_PTE; i++)
    {
        page_directory[i].val = 0x0;
        page_directory[i].kilo.r_w = 1;
    }

    /*Setting up first page directory entry for video memory*/
    page_directory[0].val = (unsigned int)video_mem_page_table;
    page_directory[0].kilo.r_w = 1;
    page_directory[0].kilo.present = 1;

    /*Setting up second page directory entry for kernel memory*/
    page_directory[1].val = (PHYSICAL_ADDR_OF_KERNEL_MEM);
    page_directory[1].mega.present = 1;
    page_directory[1].mega.r_w = 1;
    page_directory[1].mega.pg_size = 1;
    page_directory[1].mega.pcd = 1;
    page_directory[1].mega.glob = 1;

    /*Setting up page directory entry for first process*/
    page_directory[_128_MB].val = ACTUAL_128MB_PHY_ADDR;
    page_directory[_128_MB].mega.present = 1;
    page_directory[_128_MB].mega.r_w = 1;
    page_directory[_128_MB].mega.pg_size = 1;
    page_directory[_128_MB].mega.pcd = 1;
    page_directory[_128_MB].mega.u_s = 1;

    

}


/* 
 *  setup_video_memory_page_table
 *   DESCRIPTION: Fills up the all 1024 entries for the page table which will point to physical memory that contains video memory.
 *   INPUTS: NIL
 *   OUTPUTS: All 1024 entries of page table filled up
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */

void setup_video_memory_page_table()
{
    int i;
    for(i=0; i<NUMBER_OF_PDE_OR_PTE; i++)
    {
        video_mem_page_table[i].val = (i<<SETTING_BIT_12_TO_21_OF_PTE);
        video_mem_page_table[i].r_w = 1;
    }

    /*Setting up present and r/w bits for page table entry*/
    video_mem_page_table[PHYSICAL_ADDR_OF_VIDEO_MEM].r_w = 1;
    video_mem_page_table[PHYSICAL_ADDR_OF_VIDEO_MEM].present = 1;
}

/* 
 *  enable_paging
 *   DESCRIPTION: Enables paging
 *   INPUTS: pointer to the first entry in page directory table
 *   OUTPUTS: NIL
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */

int enable_paging(unsigned int* page_directory)
{
    if(page_directory==NULL)
    {
        return -1;
    }
    asm volatile (" movl %0,%%eax\n"
    "movl %%eax, %%cr3\n"
    "movl %%cr4, %%eax\n"
    "orl $0x00000010, %%eax\n"
    "movl %%eax, %%cr4\n"
    "movl %%cr0,%%eax\n"
    "orl $0x80000000,%%eax\n"
            "movl %%eax,%%cr0\n"
            :
            : "r"(page_directory)
            : "%eax"

        );
    return 0;
}

/* 
 *  swap_page
 *   DESCRIPTION: changes the physical address 128MB(virtual memory) points to. flushes the TLB
 *   INPUTS: process_addr
 *   OUTPUTS: NIL
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */

void swap_page(uint32_t process_addr){

    page_directory[_128_MB].val = process_addr;
    page_directory[_128_MB].mega.present = 1;
    page_directory[_128_MB].mega.r_w = 1;
    page_directory[_128_MB].mega.pg_size = 1;
    page_directory[_128_MB].mega.pcd = 1;
    page_directory[_128_MB].mega.u_s = 1;
    
    asm volatile(
    "mov %%cr3, %%eax;"
    "mov %%eax, %%cr3;"
    :                      
    :                      
    :"%eax"                
        );
}

/* 
 *  set_user_vmem
 *   DESCRIPTION: sets up page directory entry 34 to point  to user_vmem_table and initliaze the values
 *   INPUTS: NIL
 *   OUTPUTS: NIL
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */

void set_user_vmem (){
    page_directory[_132_MB].val = (unsigned int)user_vmem_table;
    page_directory[_132_MB].kilo.r_w = 1;
    page_directory[_132_MB].kilo.present = 1;
    page_directory[_132_MB].kilo.u_s = 1;

    int i;
    for(i=0; i<NUMBER_OF_PDE_OR_PTE; i++)
    {
        user_vmem_table[i].val = (i<<SETTING_BIT_12_TO_21_OF_PTE);
        user_vmem_table[i].r_w = 1;
    }

    /*Setting up present and r/w bits for page table entry*/
    user_vmem_table[0].val = VMEM_ADDR;
    user_vmem_table[0].r_w = 1;
    user_vmem_table[0].present = 1;
    user_vmem_table[0].u_s = 1;

    asm volatile(
    "mov %%cr3, %%eax;"
    "mov %%eax, %%cr3;"
    :                      
    :                      
    :"%eax"                
    );
}

/* 
 *  set_temp_vmem
 *   DESCRIPTION: sets up a temporary memory location for video memory. 
 *   INPUTS: NIL
 *   OUTPUTS: NIL
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */

void set_temp_vmem (){
    page_directory[_132_MB].val = (unsigned int)user_vmem_table;
    page_directory[_132_MB].kilo.r_w = 1;
    page_directory[_132_MB].kilo.present = 1;
    page_directory[_132_MB].kilo.u_s = 1;

    int i;
    for(i=0; i<NUMBER_OF_PDE_OR_PTE; i++)
    {
        user_vmem_table[i].val = (i<<SETTING_BIT_12_TO_21_OF_PTE);
        user_vmem_table[i].r_w = 1;
    }

    /*Setting up present and r/w bits for page table entry*/
    user_vmem_table[0].val = TEMP_VMEM;
    user_vmem_table[0].r_w = 1;
    user_vmem_table[0].present = 1;
    user_vmem_table[0].u_s = 1;

    asm volatile(
    "mov %%cr3, %%eax;"
    "mov %%eax, %%cr3;"
    :                      
    :                      
    :"%eax"                
    );
}
