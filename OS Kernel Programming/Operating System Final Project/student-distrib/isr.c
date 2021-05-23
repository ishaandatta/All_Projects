#include "lib.h"
#include "isr.h"
#include "keyboard.h"
#include "i8259.h"
#include "syscall.h"
#include "filesystem.h"
#include "rtc.h"
#include "scheduling.h"
#include "task.h"

#define RTC_DATA    0x71
#define RTC_REG     0x70
#define NUM_EXCEPTIONS 32
#define REG_C 0x0C
#define RTC_IRQ_NUM 40
#define KEYBOARD_IRQ_NUM 33
#define PIT_IRQ_NUM     32
#define SYSTEM_CALL     0x80

#define RTC_IRQ 8 // rtc irq number

char test_rtc_c = '1';


/* 
 *  isr_handler
 *   DESCRIPTION: Depending on the value of the interrupt number, call the respective functions to execute
 *                If it's rtc interrupt, call test_interrupt()
 *                If it's keyboard interrupt, call keyboard_display()
 *                If it's an exception, call exception_handler()
 *   INPUTS: r (registers_t struct)
 *   OUTPUTS: NIL
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */
int32_t isr_handler (registers_t r){
    if (r.int_no == RTC_IRQ_NUM){ // rtc interrupt
        send_eoi(RTC_IRQ);
        outb(REG_C, RTC_REG);	// select register C
        inb(RTC_DATA);
        cli();
        rtc_flag = 1;
        sti();
        return 0;
    }
    else if (r.int_no == KEYBOARD_IRQ_NUM){ // keyboard interrupt
        send_eoi(1);
        keyboard_display();
        return 0;
    }
    else if (r.int_no == PIT_IRQ_NUM){ // PIT interrupts
        send_eoi(0);
        scheduler_tick();
        return 0;
    }
    else if (r.int_no == SYSTEM_CALL){ // system calls
        return syscall_handler(r.eax, r.ebx, r.ecx, r.edx);
    }
    else{
        printf("eip: %x", r.eip);
        printf("ebp: %x", r.ebp);
        printf("eax: %x", r.eax);
        printf("Received interrupt: %d\n", r.int_no);
        exception_handler(r.int_no);
        stop(-1);
        // asm volatile ("hlt"); // halt after receiving exception
        return 0;
    }
}

/* 
 *  syscall_handler
 *   DESCRIPTION: Execute system call depending on the cmd (eax) number
 *   INPUTS: eax, ebx, ecx, edx values
 *   OUTPUTS: dependent on the system call
 *   RETURN VALUE: return value of the system call
 *   SIDE EFFECTS: executes system call
 */
int32_t syscall_handler(uint32_t eax,uint32_t ebx, uint32_t ecx, uint32_t edx ){
    if (eax == 1){ // halt
        return halt((uint8_t)(ebx));
    }
    if (eax == 2){ // execute
        return execute((uint8_t*)(ebx));
    }
    if (eax == 3){ // read command
        return read((int32_t)ebx, (void*)ecx, (int32_t)edx);
    }
    if (eax == 4){  // write command
        return write((int32_t)ebx, (void*)ecx, (int32_t)edx);
    }
    if (eax == 5){  // open system call
        return fopen((uint8_t*) ecx);
    }
    if (eax == 6){ // close system call
        return close((int32_t)ebx);
    }
    return -1;
}

/* 
 *  exception_handler
 *   DESCRIPTION: Depending on the value of the interrupt number, output the various error messages
 *   INPUTS: excception number
 *   OUTPUTS: an error message that corresponds to the error being committed
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */
int exception_handler(int exception_num){
    if (exception_num >= NUM_EXCEPTIONS){
        return -1;
    }
    switch (exception_num){
        case(0):
            printf("Divide Error");
            break;
        case(1):
            printf("Exception Received"); // intel reserved exception
            break;
        case(2):
            printf("NMI Interrupt");
            break;
        case(3):
            printf("Breakpoint Exception");
            break;
        case(4):
            printf("Overflow Exception");
            break;
        case(5):
            printf("BOUND Range Exception");
            break;
        case(6):
            printf("Invalid Opcode");
            break;
        case(7):
            printf("Device not Available");
            break;
        case(8):
            printf("Double Fault");
            break;
        case(9):
            printf("Coprocessor Segment Overrun");
            break;
        case(10):
            printf("Invalid TSS");
            break;
        case(11):
            printf("Segment not Present");
            break;
        case(12):
            printf("Stack-Segment Fault");
            break;
        case(13):
            printf("General Protection");
            break;
        case(14):
            printf("Page Fault");
            break;
        case(15):
            printf("Exception Received"); // intel reserved
            break;
        case(16):
            printf("x87 FPU Floating Point Error");
            break;
        case(17):
            printf("Alignment Check");
            break;
        case(18):
            printf("Machine Check");
            break;
        case(19):
            printf("SIMD Floating Point Exception");
            break;       
    }
    return 0;
}
