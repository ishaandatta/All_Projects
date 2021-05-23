#include "scheduling.h"
#include "lib.h"
#include "x86_desc.h"
#include "task.h"
#include "types.h"
#include "terminal.h"
#include "i8259.h"

#define DEFAULT_FREQUENCY   1193180
#define PIT_CHANNEL0_PORT       0x40
#define PIT_COMMAND_PORT        0x43
#define SQUARE_WAVE_GEN         0x36
#define EIGHT_BIT_SHIFT         8

int8_t sched_count = -1;


/* 
 *  init_pit
 *   DESCRIPTION: initializes pit to the input frequency
 *   INPUTS: frequency for PIT to be initialized to
 *   OUTPUTS: NIL
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: context switch to next process
 */
void init_pit(int frequency){
    uint8_t divisor = DEFAULT_FREQUENCY / frequency;      
    outb(SQUARE_WAVE_GEN, PIT_COMMAND_PORT); // we are using mode 3, the square wave generator
    outb(divisor & EIGHT_BIT_MASK, PIT_CHANNEL0_PORT);
    outb(divisor >> EIGHT_BIT_SHIFT, PIT_CHANNEL0_PORT); // write to next 8 bits of port
    enable_irq(0); // enables interrupts from PIT
}


/* 
 *  scheduler_tick
 *   DESCRIPTION: executes after every tick of the PIT, performs a context switch to the 
 * next process to be scheduled
 *   OUTPUTS: NIL
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: context switch to next process
 */

void scheduler_tick(){
    // printf("scheduler_tick\n");
    while(1)
    {
        cli();
        sched_count++;
        if (sched_count >=MAX_PROCESS)
        {
            sched_count = 0;
        }
        pcb_t* new_pcb = (pcb_t*) (MB_8 - KB_8 * (sched_count + 1));
        if ((process_bitmask & (1 << sched_count)) > 0 && new_pcb->active == 1 )
        {
            break;
        }
        sti();
    }
    if (sched_count != current_process_num){
        context_switch(sched_count);
    }
}
