
# macros for ISRs with and without error codes
/* 
 *  ISR_NOERRCODE\ISR_ERRCODE
 *   DESCRIPTION: For interrupts that do not push error code, this function will help push a dummy error code
 *                It also pushes the interrupt number as an argument for the function isr_haandler which
 *                will be called in isr_common
 *   INPUTS: NIL
 *   OUTPUTS: NIL
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */
.macro ISR_NOERRCODE n 
  .globl isr\n        
  isr\n:
    cli
    pushl $0
    pushl $\n
    jmp isr_common
.endm

.macro ISR_ERRCODE n
  .globl isr\n
  isr\n:
    cli
    pushl $\n
    jmp isr_common
.endm

ISR_NOERRCODE 0
ISR_NOERRCODE 1
ISR_NOERRCODE 2
ISR_NOERRCODE 3
ISR_NOERRCODE 4
ISR_NOERRCODE 5
ISR_NOERRCODE 6
ISR_NOERRCODE 7
ISR_ERRCODE 8
ISR_NOERRCODE 9
ISR_ERRCODE 10
ISR_ERRCODE 11
ISR_ERRCODE 12
ISR_ERRCODE 13
ISR_ERRCODE 14
ISR_NOERRCODE 15
ISR_NOERRCODE 16
ISR_ERRCODE 17
ISR_NOERRCODE 18
ISR_NOERRCODE 19
ISR_NOERRCODE 20
ISR_NOERRCODE 21
ISR_NOERRCODE 22
ISR_NOERRCODE 23
ISR_NOERRCODE 24
ISR_NOERRCODE 25
ISR_NOERRCODE 26
ISR_NOERRCODE 27
ISR_NOERRCODE 28
ISR_NOERRCODE 29
ISR_NOERRCODE 30
ISR_NOERRCODE 31

ISR_NOERRCODE 32

ISR_NOERRCODE 33
ISR_NOERRCODE 40

.globl idt_flush, isr128

/* 
 *  idt_flush
 *   DESCRIPTION: Tells the processor where the IDT is located
 *   INPUTS: pointer to the first entry of the IDT
 *   OUTPUTS: NIL
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */
idt_flush:
    movl 4(%esp), %eax
    lidt (%eax)
    ret

/* 
 *  isr_common
 *   DESCRIPTION: prepares the argument (registers_t), pushing all general purpose registers and data segment selector
 *                argument interrupt number and push code had already been pushed in macros for ISr with and without error codes
 *   INPUTS: NIL
 *   OUTPUTS: NIL
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */
isr_common:
 # pushes general purpose registers
  pushl %edi
  pushl %esi
  pushl %ebp
  pushl %esp
  pushl %ebx
  pushl %edx
  pushl %ecx
  pushl %eax  
               
  movw %ds, %bx              
  pushl %ebx                 # pushes data segment descriptor

  movw $0x10, %bx
  movw %bx, %ds
  movw %bx, %es
  movw %bx, %fs
  movw %bx, %gs

  call isr_handler
  popl %ebx        # pops data segment descriptor
  movw %bx, %ds
  movw %bx, %es
  movw %bx, %fs
  movw %bx, %gs

  # pops general purpose registers
  addl $4, %esp # pop pushed eax value
  popl %ecx
  popl %edx
  popl %ebx
  popl %esp
  popl %ebp
  popl %esi
  popl %edi
  addl $8, %esp   # pops args (error code and int number)
  sti            # enable interrupts
  iret           # return from function
  
isr128:
     # pushes general purpose registers
  cli
  pushl %edi
  pushl %esi
  pushl %ebp
  # pushl %esp
  pushl %edx
  pushl %ecx
  pushl %ebx
  cmpl $10, %eax 
  jg err
  cmpl $0, %eax
  jle err
  call *jump_table(,%eax,4)
  jmp no_err
  # pops general purpose registers
err:
  movl $-1, %eax # invalid system call number
 no_err:
  popl %ebx
  popl %ecx
  popl %edx
  # popl %esp
  popl %ebp
  popl %esi
  popl %edi
  sti            # enable interrupts
  iret           # return from function

jump_table:
  .long 0x0, halt, execute, read, write, open, close, getargs , vidmap, set_handler, sigreturn
