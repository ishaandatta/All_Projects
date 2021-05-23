/* i8259.c - Functions to interact with the 8259 interrupt controller
 * vim:ts=4 noexpandtab
 */

#include "i8259.h"
#include "lib.h"

#define PIC_MASTER   0x20
#define PIC_SLAVE   0xA0
#define PIC_MASTER_DATA    (PIC_MASTER + 1)
#define PIC_SLAVE_DATA  (PIC_SLAVE + 1)
#define PIC_EOI_CMD 0x20

#define ICW1_INIT	0x11		/* ICW1: Initialization command */
#define ICW2_VECTOR	0x20		/* Call address interval 4 (8) */
#define ICW3_IRNUM	0x04		/* Call address interval 4 (8) */

#define ICW2_OFFSET	0x08		/* Level triggered (edge) mode */
#define ICW3_CAS	0x02		/* Single (cascade) mode */
 
#define NORMAL_EOI	0x01		/* 8086/88 (MCS-80/85) mode */
#define AUTO_EOI	0x03		/* Auto (normal) EOI */

#define IRQ_MAX 15
#define THREE_LSB_MASK 0x7

/* Interrupt masks to determine which interrupts are enabled and disabled */
uint8_t master_mask; /* IRQs 0-7  */
uint8_t slave_mask;  /* IRQs 8-15 */

/* 
 *  i8259_init
 *   DESCRIPTION: Initialize the 8259 PIC. First masks all interrupts, then send
 *                  each control word for initialization. See in-line comments for 
 *                  explanation about the control words. Exits with restoring the
 *                  state of the masks on each PIC. 
 *   INPUTS: NIL
 *   OUTPUTS: 
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: PIC (master and slave) are initialized in normal EOI mode
 */
void i8259_init(void) {
    master_mask = inb(PIC_MASTER_DATA);
    slave_mask = inb(PIC_SLAVE_DATA);

    outb(0xFF, PIC_MASTER_DATA);   //mask all master interrupts
    // io_wait();
    outb(0xFF, PIC_SLAVE_DATA);     //mask all slave interrupts
    // io_wait();

    outb(ICW1_INIT, PIC_MASTER);         //Send ICW1 to master
    // io_wait();
    outb(ICW2_VECTOR, PIC_MASTER_DATA);         //send ICW2: master ir0-7 mapped to 0x20-0x27
    outb(ICW3_IRNUM, PIC_MASTER_DATA);          //ICW3: set slave pic at ir2
    outb(NORMAL_EOI, PIC_MASTER_DATA);          //ICW4: signal normal EOI

    outb(ICW1_INIT, PIC_SLAVE);                             //Send ICW1 to slave
    outb(ICW2_VECTOR + ICW2_OFFSET, PIC_SLAVE_DATA);        //send ICW2: slave ir0-7 mapped to 0x28-0x2f
    outb(ICW3_CAS, PIC_SLAVE_DATA);                         //ICW3: send slave its CAS identity (ir2)
    outb(NORMAL_EOI, PIC_SLAVE_DATA);                       //ICW4: signal normal EOI

    outb(master_mask, PIC_MASTER_DATA);   //restore master interrupt mask
    // io_wait();
    outb(slave_mask, PIC_SLAVE_DATA);     //restore slave interrupt mask
    // io_wait();
}

/* 
 *  enable_irq
 *   DESCRIPTION: Enable (unmask) the specified IRQ number
 *   INPUTS: irq_num - the IR number on the PIC to be enabled
 *   OUTPUTS: NIL
 *   RETURN VALUE: Returns 0 on success
 *   SIDE EFFECTS: Specific IRQ number is enabled
 */
int enable_irq(uint32_t irq_num) {
    if (irq_num < 0 || irq_num > IRQ_MAX){
        return -1;
    }
    uint32_t value;
    uint32_t port = irq_num>=8?PIC_SLAVE_DATA:PIC_MASTER_DATA; /*if irq number is greater or equal to 8, it is from the slave PIC*/
    value = inb(port) & (0xFF^(1 << (irq_num&THREE_LSB_MASK))); /*unmask the irq at that specific bit*/
    // if (irq_num >= 8){
    //     irq_num -= 8;
    // }
    // value = inb(port) & ~(1 << (irq_num & 0xFF));
    outb(value, port);  
    return 0;     
}

/* 
 *  disable_irq
 *   DESCRIPTION: Disable (mask) the specified IRQ number
 *   INPUTS: irq_num - the IR number on the PIC to be disabled
 *   OUTPUTS: NIL
 *   RETURN VALUE: Returns 0 on success
 *   SIDE EFFECTS: Specific IRQ number is disabled
 */
int disable_irq(uint32_t irq_num) 
{
    if (irq_num < 0 || irq_num > IRQ_MAX){
        return -1;
    }
    uint32_t value;
    uint32_t port = irq_num>=8?PIC_SLAVE_DATA:PIC_MASTER_DATA; /*if irq number is greater or equal to 8, it is from the slave PIC*/
    value = inb(port) | (1 << ( irq_num & THREE_LSB_MASK));
    outb(value, port); 
    return 0;
}


/* 
 *  send_eoi
 *   DESCRIPTION: Send end-of-interrupt signal for the specified IRQ
 *   INPUTS: irq_num - the IR number on the PIC corresponding to the EOI
 *   OUTPUTS: NIL
 *   RETURN VALUE: Returns 0 on success
 *   SIDE EFFECTS: PIC is signalled EOI
 */
int send_eoi(uint32_t irq_num) 
{
    if (irq_num < 0 || irq_num > IRQ_MAX){
        return -1;
    }
    if(irq_num >= 8)
    {
        outb(PIC_EOI_CMD, PIC_MASTER);
        outb(PIC_EOI_CMD, PIC_SLAVE);
    }
    else
    {
        outb(PIC_EOI_CMD, PIC_MASTER);
    }
    return 0;
}
