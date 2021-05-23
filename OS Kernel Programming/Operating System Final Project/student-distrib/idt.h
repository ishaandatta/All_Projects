/* Function headers relevant to idt initiazliation etc. */

# include "lib.h"
# include "x86_desc.h"

/* The IDT itself (declared in x86_desc.S */
extern idt_desc_t idt[NUM_VEC];
/* The descriptor used to load the IDTR */
extern x86_desc_t idt_desc_ptr;
/* updates idtr */

extern void init_idt();

/*setting the value of the IDT entry*/
extern int set_gate(uint8_t int_num, uint32_t base, uint16_t selector);

extern void (*isr_arr[])(void);
/*The different functions for the different interrupts to be called*/
extern void isr0 ();
extern void isr1 ();
extern void isr2 ();
extern void isr3 ();
extern void isr4 ();
extern void isr5 ();
extern void isr6 ();
extern void isr7 ();
extern void isr8 ();
extern void isr9 ();
extern void isr10 ();
extern void isr11 ();
extern void isr12 ();
extern void isr13 ();
extern void isr14 ();
extern void isr15 ();
extern void isr16 ();
extern void isr17 ();
extern void isr18 ();
extern void isr19 ();
extern void isr20 ();
extern void isr21 ();
extern void isr22 ();
extern void isr23 ();
extern void isr24 ();
extern void isr25 ();
extern void isr26 ();
extern void isr27 ();
extern void isr28 ();
extern void isr29 ();
extern void isr30 ();
extern void isr31 ();
extern void isr32 ();
extern void isr33 ();
extern void isr40 ();
extern void isr128 ();


int set_user_gate(uint8_t int_num, uint32_t base, uint16_t selector);
