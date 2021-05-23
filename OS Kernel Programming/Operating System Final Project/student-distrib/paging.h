#include "multiboot.h"
#include "x86_desc.h"
#include "lib.h"
#include "i8259.h"
#include "debug.h"
#include "tests.h"
#include "idt.h"
#include "rtc.h"

extern void setup_page_directory();
extern void setup_video_memory_page_table();
extern int enable_paging(unsigned int* page_directory);
void swap_page(uint32_t process_addr);
void set_user_vmem ();
void set_temp_vmem ();


typedef struct __attribute__((packed)) mega_page_directory_entry_t
{
    uint32_t present : 1;
    uint32_t r_w : 1;
    uint32_t u_s : 1;
    uint32_t pwt : 1;
    uint32_t pcd : 1;
    uint32_t accessed : 1;
    uint32_t dirty : 1;
    uint32_t pg_size : 1;
    uint32_t glob : 1;
    uint32_t avail : 3;
    uint32_t pat : 1;
    uint32_t reserved :9;
    uint32_t page_base_address : 10;
} mega_page_directory_entry_t;

typedef struct __attribute__((packed)) kilo_page_directory_entry_t
{
    uint32_t present : 1;
    uint32_t r_w : 1;
    uint32_t u_s : 1;
    uint32_t pwt : 1;
    uint32_t pcd : 1;
    uint32_t accessed : 1;
    uint32_t ignore : 1;
    uint32_t pg_size : 1;
    uint32_t glob : 1;
    uint32_t avail : 3;
    uint32_t page_table_address :20;
} kilo_page_directory_entry_t;

typedef struct page_directory_entry_t
{
    union
    {
        uint32_t val;
        mega_page_directory_entry_t mega;
        kilo_page_directory_entry_t kilo;
    };
}page_directory_entry_t ;


typedef union page_table_entry_t
{
    uint32_t val;
    struct
    {
        uint32_t present : 1;
        uint32_t r_w : 1;
        uint32_t u_s : 1;
        uint32_t pwt : 1;
        uint32_t pcd : 1;
        uint32_t accessed : 1;
        uint32_t ignore : 1;
        uint32_t pat : 1;
        uint32_t glob : 1;
        uint32_t avail : 3;
        uint32_t page_address :20;
    } __attribute__((packed));
} page_table_entry_t ;

extern page_directory_entry_t page_directory[1024];
page_directory_entry_t page_directory[1024] __attribute__((aligned(4096)));

page_table_entry_t video_mem_page_table[1024] __attribute__((aligned(4096)));
page_table_entry_t user_vmem_table[1024] __attribute__((aligned(4096)));

