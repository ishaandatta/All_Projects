/* Functions relevant to idt initiazliation etc. */

# include "idt.h"
# include "x86_desc.h"

/* The IDT itself (declared in x86_desc.S */
idt_desc_t idt[NUM_VEC];
/* The descriptor used to load the IDTR */
x86_desc_t idt_desc_ptr;
/* updates idtr */

extern void idt_flush(uint32_t); 

#define NUMBER_OF_IDT_ENTRIES 256
#define GET_16_LSB 16
#define NUM_EXCEPTIONS 32


// array of fucntion pointers for the first 32 isr handlers
void (*isr_arr[])(void) = {isr0, isr1, isr2, isr3, isr4, isr5, isr6, isr7, isr8, isr9, isr10, isr11, isr12, isr13, isr14, isr15, isr16, 
isr17, isr18, isr19, isr20, isr21, isr22, isr23, isr24, isr25, isr26, isr27, isr28, isr29, isr30, isr31};

/* 
 *  init_idt
 *   DESCRIPTION: Tells the processor where the IDT is located (this is done via idt_flush)
 *                Fills up all 256 entries of the IDT. Each IDT entry is 64 bits long. IDT entry is 
 *                filled up using set_gate function
 *   INPUTS: NIL
 *   OUTPUTS: All 256 entries of IDT filled up. CPU knows where IDT is located. IDT is initialized
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */

void init_idt(){
    int i;
    idt_desc_ptr.size = sizeof(idt_desc_t) * NUMBER_OF_IDT_ENTRIES - 1; // init the idt_desc_ptr (to load into the idtr)
    idt_desc_ptr.addr = (uint32_t)idt;
    for (i = 0; i < NUM_EXCEPTIONS; i++){
        set_gate(i, (uint32_t)isr_arr[i], KERNEL_CS);
    }    
    set_gate(32, (uint32_t)isr32, KERNEL_CS); // set gate for keyboard
    set_gate(33, (uint32_t)isr33, KERNEL_CS); // set gate for keyboard
    set_gate(40, (uint32_t)isr40, KERNEL_CS); // set gate for rtc
    set_user_gate(128, (uint32_t)isr128, KERNEL_CS); // set gate for system calls

    idt_flush((uint32_t)&idt_desc_ptr+2); /*access the size member of x86_desc_t instead of padding member*/
}

/* 
 *  set_gate
 *   DESCRIPTION: Fills up the 64 bits value for each IDT entry
 *   INPUTS: int_num - the index into the idt array of 256
 *           base - the  32 bits address separated into first 15 and last bits of IDT entry
 *           selector - 16 bit value determining the segment selector (kernel code, kernel data, user code, user data) 
 *   OUTPUTS: All 64 bits of IDT entry filled up
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */

int set_gate(uint8_t int_num, uint32_t base, uint16_t selector){
        if((base==0x0) || (selector != KERNEL_CS))
        {
            return -1;
        }
        idt[int_num].offset_15_00 = base & SIXTEEN_BIT_MASK; // gets first 16 bits of base 
        idt[int_num].seg_selector = selector;
        idt[int_num].reserved4 = 0; // 8 bits
        idt[int_num].reserved3 = 1;
        idt[int_num].reserved2 = 1;
        idt[int_num].reserved1 = 1;
        idt[int_num].size = 1; // said by Fang, for backward compatibility
        idt[int_num].reserved0 = 0; 
        idt[int_num].dpl = 0;       
        idt[int_num].present = 1;
        idt[int_num].offset_31_16 = (base >> GET_16_LSB) & SIXTEEN_BIT_MASK; // gets last 16 bits of base
        return 0;
}

int set_user_gate(uint8_t int_num, uint32_t base, uint16_t selector){
        if((base==0x0) || (selector != KERNEL_CS))
        {
            return -1;
        }
        idt[int_num].offset_15_00 = base & SIXTEEN_BIT_MASK; // gets first 16 bits of base 
        idt[int_num].seg_selector = selector;
        idt[int_num].reserved4 = 0; // 8 bits
        idt[int_num].reserved3 = 1;
        idt[int_num].reserved2 = 1;
        idt[int_num].reserved1 = 1;
        idt[int_num].size = 1; // said by Fang, for backward compatibility
        idt[int_num].reserved0 = 0; 
        idt[int_num].dpl = 3;       
        idt[int_num].present = 1;
        idt[int_num].offset_31_16 = (base >> GET_16_LSB) & SIXTEEN_BIT_MASK; // gets last 16 bits of base
        return 0;
}
