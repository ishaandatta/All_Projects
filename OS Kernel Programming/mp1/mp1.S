
# mp1.S - life-or-death version
# Good luck, and have fun!

.data

    # Constants for accessing the fields of a struct keystroke_args
    # struct keystroke_args is defined in rtc.h and mp1.h

	KA_SIZE	  = 14   # 14 bytes when copying
	KA_STACK  = 16   # use 16 bytes on stack for alignment
	DIRECTION = 0
	SELECTOR  = 2
	GUESS     = 4
	HINT      = 9

    # Constants for accessing the fields of a struct game_status
    # struct game_status is defined in rtc.h and mp1.h

	GS_SIZE   = 8	# 8 bytes
	POP 	  = 0
	INF	  = 4

    # Constants for screen size

    	SCR_WIDTH  = 80
	SCR_HEIGHT = 20
	SCR_SIZE   = ((SCR_WIDTH) * (SCR_HEIGHT))

    # ASCII cell images

        CELL_LIVE = 0x78
	CELL_DEAD = 0x20
  ROW_OFFSET = 3520


# Data shared between this file and rtc.c helper functions

# This '.globl' directive makes these symbols visible externally
.globl rand_seed, aggression

			.align 8
rand_seed:		.quad 0x0	# Pseudo-random number seed
aggression:		.long 0x0	# Aggression level of virus


# Data private to this file

current_board:		.long 0x0	# Address of current board
next_board:		.long 0x0	# Address of next board
population:		.long 0x0	# Remaining human population
infection:		.long 0x0	# Count of live virus cells
select_image:		.string "==>"	# Picture of the selector
select_blank:		.string "   "	# Picture to overwrite selector
base_array:             .string "ACGT"  # Array of characters for bases
live_total:   .long 0x0   # Count of live cells

.text

# void mp1_poke(void);
# You can use this function to write to video memory.
#
# Interface: Register-based arguments (not C-style)
#    Inputs: %cl  - The byte you wish to write
#            %eax - Offset from the start of video memory that you wish
#                   to write to
#   Outputs: Text-mode video screen is written to at location %eax with
#            the byte in %cl
# Registers: Clobbers EDX

mp1_poke:
		movl    vmem_base_addr(,1),%edx
		movb    %cl,(%edx,%eax,1)
		ret

#   ----------------- Exported functions ---------------------

# void mp1_rtc_tasklet(unsigned long ignore);
# Performs three tasks:
#	(1) updates the life game board and calculates infection count
#	(2) swaps the two boards
#	(3) applies population reduction based on infection count
#	(4) redraws the screen
#	(5) notifies the user code by calling mp1_notify_user
# Inputs   : none
# Outputs  : none
# Registers: Standard C calling convention
#			live_total -> live neighbour Count
#     EBX -> Cell offset
#			EDI -> cell address
#			ESI -> Column counter
#			ECX -> Row counter

.globl mp1_rtc_tasklet
mp1_rtc_tasklet:

    pushl %ebp
    movl  %esp, %ebp 
    pushl %esi                       # callee-save registers
    pushl %edi
    pushl %ebx
    cmpl  $0, current_board          # check if current_board non-zero
    je    Return
    xorl  %esi, %esi						     
    xorl  %ecx, %ecx
    movl  $1, %ecx                   # init row counter to 1

Outerloop:                           # iterate over rows
    movl	$1, %esi                   # init column counter to 1
Innerloop:                           # iterate over columns
		# caller-setup for neighbor_count
    pushl	%ecx							          
    pushl %esi
    movl  %ecx, %edi
    imull $SCR_WIDTH, %edi            # row number*80
    addl  %esi, %edi                  
    movl  %edi, %ebx                  # ebx = cell offset (column+ row*80)
    addl  current_board, %edi 
    
    pushl	%edi	                      # push address of current cell
    call	neighbor_count

    popl	%edi                        # load cell address
    # caller-setup for tick_result
    pushl	%eax                        # push neighbor count
    xorl  %eax, %eax
    movb (%edi), %al	                # get value of current cell and push it
    pushl	%eax							            
    call	tick_result
    addl	$8, %esp
    addl  next_board, %ebx              # address to be updated
    movl  %eax, (%ebx) 	                # save next value of cell
		     			      	
    addl  %eax, (live_total)            # add cell value to total live count
    popl  %esi
    incl	%esi						            	# increment column
    popl	%ecx
    cmpl	$80, %esi
    jl		Innerloop						          # loop for each cell in the row
    incl	%ecx
    cmpl	$20, %ecx
    jl		Outerloop               
    # loop ends, store infection value
    movl  live_total, %eax
    imull $10, %eax
    movl	%eax, infection	            	# store curr infection value
    movl  $0, live_total
    # swap boards
    movl	current_board, %edi
    movl	next_board, %edx
    movl	%edx, current_board
    movl	%edi, next_board
    # set new population
    movl	infection, %edi
    movl	population, %edx
    cmpl	%edi, %edx
    jb    Zero_population
    subl  %edi, population
Continue:
    # draw screen
    pushl	%ecx
    pushl	%eax
    pushl	%edx
    call draw_screen
    popl  %edx
    popl  %eax
    popl  %ecx
    call  mp1_notify_user
    # callee convention		
    #	movl %e x, %eax  #ret value
Return:	
    popl %ebx
    popl %edi
    popl %esi
    leave
    ret 
Zero_population:
    movl  $0, population
    jmp   Continue

# int mp1_ioctl(unsigned long arg, unsigned int cmd)
# The dispatch function for the MP1 ioctls - should use the cmd argument
# and a jumptable to execute one of the specific ioctls implemented below.
# Inputs   : unsigned long arg - parameter to the mp1_ioctl_....
#          : unsigned int cmd  - specifies which mp1_ioctl_... function
#          :                     to execute
# Outputs  : Returns an integer - depends on which ioctl() function is called
# Registers: Standard C calling convention
jump_table:
    .long mp1_ioctl_startgame
    .long mp1_ioctl_endgame
    .long mp1_ioctl_keystroke
    .long mp1_ioctl_getstatus
    .long mp1_ioctl_vaccinate


.globl mp1_ioctl
mp1_ioctl:
    movl  8(%esp), %eax     # eax <- cmd
    cmpl  $0, %eax          # check bounds
    jb    INVALID
    cmpl  $4, %eax
    ja    INVALID
    jmp   *jump_table(, %eax, 4)
    leave
    ret

INVALID:
    movl   $-1, %eax
    leave
    ret


# ----------------- Functions private to this file -------------------


draw_screen:
	# For simplicity, your implementation may assume a SCR_WIDTH of 80.
  # ESI = number of cells iterated
  # EAX = offset from start of video memory
  # EBX = memory address of current cell
  # EDI = temp variable
		pushl %ebp			            # maintain base pointer
		movl %esp, %ebp
    pushl %esi			            # callee-save Register
		pushl %edi
		pushl %ebx
    xorl  %esi, %esi

draw_screen_loop:
    cmpl  $1599, %esi
    jae    draw_screen_complete    
    incl  %esi
    movl  %esi, %ebx            # ebx = cell index
    movl  $2, %eax              
    imull %ebx, %eax            # eax = 2*cell index (cell offset)

    movl  %esi, %edi
    addl  current_board, %edi   # edi = current cell address (in board)
    movb  (%edi), %cl           # cl = current cell value
    cmpb  $0, %cl
    je    dead_cell
    movb  $CELL_LIVE, %cl
    call mp1_poke
    jmp  draw_screen_loop
dead_cell:
    movb  $CELL_DEAD, %cl     
    call  mp1_poke
    jmp   draw_screen_loop
    
draw_screen_complete:
    popl  %ebx
    popl  %edi
    popl  %esi
    leave
    ret

# ESI = cell iterator (counter)
# EAX = temp register
mp1_ioctl_startgame:
    pushl %ebp
    movl %esp, %ebp
    pushl %esi			# callee-save Register
    pushl %edi
    pushl %ebx
    movl  $80, aggression
    movl  $8000000, population

    # set seed
    pushl 8(%ebp)
    call  seed_generator
    
    # allocate memory for boards
    pushl $1600
    call  mp1_malloc
    cmpl  $0, %eax
    je    failed_allocation
    movl  %eax, current_board
    call  mp1_malloc
    cmpl  $0, %eax
    je    failed_allocation_both
    movl  %eax, next_board
    # initialise cells
    xorl %esi, %esi
 init_cells:
    movl  current_board, %eax
    movb  $0, (%eax, %esi)
    movl  next_board, %eax
    movb  $0, (%eax, %esi)
    incl  %esi
    cmpl  $1600, %esi
    jb    init_cells
   
    pushl current_board
    call  init_virus
    movl  %eax, infection
    addl  $12, %esp
    popl  %ebx
    popl  %edi
    popl  %esi
    movl  $0, %eax
    leave
		ret
failed_allocation:
    pushl current_board
    call  mp1_free
    movl  $0, current_board
    movl  $-1, %eax
    popl  %ebx
    popl  %edi
    popl  %esi
    leave
    ret
failed_allocation_both:
    pushl current_board
    call  mp1_free
    pushl next_board
    call  mp1_free
    movl  $0, current_board
    movl  $0, next_board
    movl  $-1, %eax
    popl  %ebx
    popl  %edi
    popl  %esi
    leave
    ret

mp1_ioctl_endgame:
    pushl %ebp
    movl %esp, %ebp
    pushl %esi			# callee-save Register
    pushl %edi
    pushl %ebx
    movl current_board, %eax
    movl  $0, current_board
    pushl %eax
    call  mp1_free
    popl  %eax
    movl  next_board, %eax
    pushl %eax
    call  mp1_free
    popl  %eax
    movl  $0, next_board
    movl  $0, %eax
    popl  %ebx
    popl  %edi
    popl  %esi
    leave
		ret

# ESI = Counter
# EBX = passed Selector value
# EDI = pointer to top of stack after calling mp1_copy_from_user
# EAX = offset register
mp1_ioctl_keystroke:
    pushl %ebp
    movl  %esp, %ebp
    pushl %esi			    # callee-save
    pushl %edi
    pushl %ebx 
    cmpl  $0, 8(%ebp)   # null-check
    je    failed_copy
    subl  $KA_STACK, %esp  
    movl  %esp, %edi    # save to* in edi
    pushl $KA_SIZE      # push 'n'
    pushl 8(%ebp)      # push argument (from*)
    pushl %edi          # push to*
    call  mp1_copy_from_user
    addl  $12, %esp
    cmpl  $0, %eax
    jne   failed_copy
    movzwl  (%edi), %ecx
    movzwl  2(%edi), %ebx     # store selector value
    movl   %ebx, %eax
    jmp   *decision_table(, %ecx, 4)
    leave
		ret

decision_table:
    .long left_key
    .long down_key 
    .long right_key
    .long up_key

left_key: 
    imull   $10, %eax
    addl    $14, %eax
    imull   $2, %eax
    addl    $ROW_OFFSET, %eax # eax <- memory address
    xorl    %esi, %esi        # init counter
    # erase first char
    movb    select_blank(%esi), %cl
    pushl   %edx
    call    mp1_poke
    popl    %edx
    # erase second char
    incl    %esi
    addl    $2, %eax
    movb    select_blank(%esi), %cl
    pushl   %edx
    call    mp1_poke
    popl    %edx
    # erase third char
    incl    %esi
    addl    $2, %eax
    movb    select_blank(%esi), %cl
    pushl   %edx
    call    mp1_poke
    popl    %edx

    subl    $1, %ebx        # move selector left
    cmpl    $-1, %ebx
    je      cycle_right
    jmp     update_board
cycle_right: 
    movl    $4, %ebx 
    jmp     update_board


down_key:


right_key:
    imull   $10, %eax
    addl    $14, %eax
    imull   $2, %eax
    addl    $ROW_OFFSET, %eax # eax <- memory address
    xorl    %esi, %esi        # init counter
    # erase first char
    movb    select_blank(%esi), %cl
    pushl   %edx
    call    mp1_poke
    popl    %edx
    # erase second char
    incl    %esi
    addl    $2, %eax
    movb    select_blank(%esi), %cl
    pushl   %edx
    call    mp1_poke
    popl    %edx
    # erase third char
    incl    %esi
    addl    $2, %eax
    movb    select_blank(%esi), %cl
    pushl   %edx
    call    mp1_poke
    popl    %edx

    addl    $1, %ebx        # move selector right
    cmpl    $5, %ebx
    je      cycle_left
    jmp     update_board
cycle_left: 
    movl    $0, %ebx 
    jmp     update_board

up_key:

# update selector image on the board
update_board:
    movw    %bx, 2(%edi)      # update selector
    movl    %ebx, %eax
    imull   $10, %eax
    addl    $14, %eax
    imull   $2, %eax
    addl    $ROW_OFFSET, %eax # eax <- memory address
    xorl    %esi, %esi        # init counter
    # draw first char
    movb    select_image(%esi), %cl
    pushl   %edx
    call    mp1_poke
    popl    %edx
    # draw second char
    incl    %esi
    addl    $2, %eax
    movb    select_image(%esi), %cl
    pushl   %edx
    call    mp1_poke
    popl    %edx
    # draw third char
    incl    %esi
    addl    $2, %eax
    movb    select_image(%esi), %cl
    pushl   %edx
    call    mp1_poke
    popl    %edx

    # copy to user space
    pushl  $KA_SIZE
    pushl %edi          # push from*
    pushl 8(%ebp)      # push to* 
    call  mp1_copy_to_user
    addl  $12, %esp
    popl  %ebx
    popl  %edi
    popl  %esi
    movl  $0, %eax
    leave
		ret

failed_copy:
    popl  %ebx
    popl  %edi
    popl  %esi
    movl  $-1, %eax
    leave
    ret

# EDI = from*
# EBX = to* 
mp1_ioctl_getstatus:
    pushl %ebp
    movl  %esp, %ebp
    cmpl  $0, 8(%ebp)
    je    failed_getstatus
    pushl infection
    pushl population
    pushl $GS_SIZE      # push n
    movl  %esp, %edi
    addl  $4, %edi
    pushl %edi          # push from pointer
    movl  8(%ebp), %ebx
    pushl %ebx          # push to pointer
    call  mp1_copy_to_user
    cmpl  $0, %eax
    jne   failed_getstatus
    addl  $20, %esp
    movl  $0, %eax
    leave
		ret
failed_getstatus:
    movl  $-1, %eax
    leave
    ret

# int mp1_ioctl_vaccinate (unsigned long packed_args) 
# EBX = packed_args 
# ESI = cell iterator (counter)
# ECX = temp var to hold 100 for division
mp1_ioctl_vaccinate:
    pushl %ebp
    movl %esp, %ebp
    pushl %esi			
    pushl %edi
    pushl %ebx
    xorl  %esi, %esi
    movl  $0, %esi          # initialise iterator/counter

    movl  8(%ebp), %ebx
    movw %bx , %si     
    addw  %bx, aggression   # add low-bits to aggression
# iterate over all cells
vaccinate_loop:    
    cmpl  $1600, %esi
    jae   vaccinate_complete
    call  generate
    movl  $100, %ecx
    xorl  %edx, %edx
    idivl  %ecx
    cmp   %dx, %bx
    jbe   vaccinate_complete
    movl  current_board, %ecx
    addl  %esi, %ecx
    movb  $0, (%ecx)
    incl  %esi
    jmp   vaccinate_loop
vaccinate_complete:
    popl  %ebx
    popl  %edi
    popl  %esi
    movl  $0, %eax
    leave
		ret
