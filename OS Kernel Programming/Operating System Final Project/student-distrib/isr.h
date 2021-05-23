
#include "lib.h"


typedef struct registers{
   uint32_t ds;                  
   // uint32_t edi, esi, ebp, esp, ebx, edx, ecx, eax;  // general purpose register values
   uint32_t eax, ecx, edx, ebx, esp, ebp, esi, edi;
   uint32_t int_no, err_code;    // pushed by isr<num> handler
   uint32_t eip, cs, eflags, useresp, ss; 
} registers_t;

/*check if it's an RTC interrupt, exception called or keyboard input*/
extern int32_t isr_handler(registers_t r);

/*based on exception number, display the corresponding errorm messages*/
extern int exception_handler(int exception_num);

extern char test_rtc_c;

int32_t syscall_handler(uint32_t eax,uint32_t ebx, uint32_t ecx, uint32_t edx );
