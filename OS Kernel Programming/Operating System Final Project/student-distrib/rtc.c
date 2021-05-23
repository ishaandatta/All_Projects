#include "lib.h"
#include "types.h"
#include "rtc.h"
#include "i8259.h"

#define RTC_DATA    0x71
#define RTC_REG     0x70
#define REG_A       0X8A
#define REG_B       0x8B
#define SIXTH_BIT_MASK    0x40
#define FOUR_TO_SEVEN_MASK  0xF0    // mask to get bits 4 to 7


#define MAX_RTC_RATE 15
#define MIN_RTC_RATE 6
#define MIN_FREQ 2

volatile int rtc_flag;

/* 
 *  rtc_init
 *   DESCRIPTION: Initializes the RTC by first masking NMI's, getting the value in B,
 *                  doing a read to register B and setting its bit 6. 
 *   INPUTS: NIL
 *   OUTPUTS: 
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: RTC is initalised with its interrupts enabled
 */
void rtc_init(void)
{		
    outb(REG_B, RTC_REG);		// select register B, disable non-maskable interrupts
    char prev = inb(RTC_DATA);	// get current value in register B
    outb(REG_B, RTC_REG);		// do a read, which will set the index to register D
    outb( prev | SIXTH_BIT_MASK, RTC_DATA);	// Set bit 6 of register B by adding previous value to 0x40
    set_rtc_rate(MAX_RTC_RATE);
    enable_irq(RTC_IRQ);              //enable RTC irq
}

/* 
 *  set_rtc_rate
 *   DESCRIPTION: changes the rtc interrupt rate based on the argument given
 *   INPUTS: rate (the rate of rtc interrupt)
 *   OUTPUTS: different rtc interrupt rate 
 *   RETURN VALUE: 0 on success, -1 on failure
 *   SIDE EFFECTS: NIL
 */

void set_rtc_rate(uint32_t rate){
    uint32_t rate_ = rate;
    disable_irq(RTC_IRQ);
    outb(REG_A,RTC_REG); // set index to register A, disable NMI
    char prev = inb(RTC_DATA); // get initial value of register A
    outb(REG_A,RTC_REG); // reset index to A
    outb((prev & FOUR_TO_SEVEN_MASK) | rate_,RTC_DATA); //write only our rate to A. Note, rate is the bottom 4 bits
    enable_irq(RTC_IRQ);
}

/* 
 *  rtc_read
 *   DESCRIPTION: waits until rtc interrupt is received
 *   INPUTS: NIL
 *   OUTPUTS: NIL
 *   RETURN VALUE: 0
 *   SIDE EFFECTS: NIL
 */
int32_t rtc_read(){
    enable_irq(RTC_IRQ);
    cli();
    rtc_flag = 0;
    sti();
    while(!rtc_flag){;}
    return 0;
}

/* 
 *  rtc_write
 *   DESCRIPTION: sets frequency to user specified value
 *   INPUTS: buffer containing desired frequency
 *   OUTPUTS: NIL
 *   RETURN VALUE: 0 on success, -1 on failure
 *   SIDE EFFECTS: NIL
 */
int32_t rtc_write(const void* buf){
    if (buf == NULL){
        return - 1;
    }
    uint32_t frequency = *((uint32_t*)buf);
    uint32_t rate;
    /*check if its power of 2*/
    if ((frequency & (frequency - 1)) != 0){
        return -1;
    }
    rate = MAX_RTC_RATE;
    while(frequency != MIN_FREQ && rate != MIN_RTC_RATE){
        rate --;
        frequency = frequency>>1;   
    }
    set_rtc_rate(rate);
    return 0;
}

/* 
 *  rtc_open
 *   DESCRIPTION: sets frequency to default rate of 2Hz
 *   INPUTS: file
 *   OUTPUTS: NIL
 *   RETURN VALUE: 0 
 *   SIDE EFFECTS: NIL
 */
int32_t rtc_open(){
    enable_irq(RTC_IRQ);
    set_rtc_rate(MAX_RTC_RATE);
    return 0;
}
/* 
 *  rtc_open
 *   DESCRIPTION: NIL
 *   INPUTS: file
 *   OUTPUTS: NIL
 *   RETURN VALUE: 0 
 *   SIDE EFFECTS: NIL
 */

int32_t rtc_close(){
    return 0;
}
