#include "lib.h"
#include "filesystem.h"
#include "x86_desc.h"
#include "task.h"
#include "paging.h"
#include "types.h"
#include "terminal.h"
#include "scheduling.h"


#define MAGIC_NUM       0x464c457f // magic number for files 
#define ENTRY_POINT_OFFSET  24
#define START_ADDR      0x08048000
#define FIRST_ESP       0x7FFFFC
#define START_STACK     0x83FFFFC
#define MAX_FD      8

uint32_t process_bitmask = 0x00;
int32_t current_process_num = -1;
int32_t current_term_num;
uint8_t terminal_bitmask = 0x01;

term_t term_one;
term_t term_two;
term_t term_three;
term_t* term_arr[3] = {&term_one, &term_two, &term_three};

file_op_table_t stdin_ops = {{term_open, term_read, term_invalid, term_close}};
file_op_table_t stdout_ops = {{term_open, term_invalid, term_write, term_close}};


/* 
 *  get_curr_pcb_ptr
 *   DESCRIPTION: returns the pointer to the pcb for the current process
 *   INPUTS: NIL
 *   OUTPUTS: NIL
 *   RETURN VALUE: pointer to pcb for current process
 *   SIDE EFFECTS: NIL
 */

pcb_t* get_curr_pcb_ptr()
{
    return (pcb_t*) (MB_8 - KB_8 * (current_process_num + 1)); // get current pcb in kernel stack
}

/* 
 *  allocate_process
 *   DESCRIPTION: if there is space for more process, update process_bitmap (indicates which process number have already been taken) and return the process number allocated for this new process
 *   INPUTS: NIL
 *   OUTPUTS: NIL
 *   RETURN VALUE: process number allocated to the new process on success and -1 on failure
 *   SIDE EFFECTS: NIL
 */

uint32_t allocate_process()
{
    int i;
    for(i=0; i<MAX_PROCESS; i++)
    {
        if(!(process_bitmask&(1<<i))) // check process bitmask
        {
            process_bitmask |= (1<<i); // allocate new process on the bitmask
            return current_process_num = i;
        }
    }
    return -1;
}

/* 
 *  deallocate_process
 *   DESCRIPTION: updates the process_bitmap (freeing the current process). updates current_process_num
 *   INPUTS: NIL
 *   OUTPUTS: NIL
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */


void deallocate_process()
{
    process_bitmask ^= (1<<current_process_num); // remove a process via its bitmask
    pcb_t* curr_pcb_ptr = get_curr_pcb_ptr();
    current_process_num  = curr_pcb_ptr->parent_process_num; // update current process
}

/* 
 *  switch_to_user_mode
 *   DESCRIPTION: sets up tss for stack switching. iret to user mode
 *   INPUTS: NIL
 *   OUTPUTS: NIL
 *   RETURN VALUE: entry_point
 *   SIDE EFFECTS: NIL
 */

void switch_to_user_mode(uint32_t entry_point)
{
   // Set up a stack structure for switching to user mode.
    tss.ss0 = KERNEL_DS; 
    tss.esp0 = FIRST_ESP - (KB_8 * current_process_num); // kernel stack
   // Set up a stack structure for switching to user mode.
   asm volatile("  \
     cli; \
     andl $0xFF, %%ebx; \
     movl %%ebx, %%eax; \
     mov %%ax, %%ds; \
     movl %1, %%eax; \
     pushl %%ebx; \
     pushl %%eax; \
     pushfl; \
     popl %%eax; \
     orl %4, %%eax; \
     pushl %%eax ;\
     pushl %2; \
     pushl %0; \
     iret;\
     "
     : 
     :"r" (entry_point), "r" (START_STACK), "r" (USER_CS), "b"(USER_DS), "r"(0x200)
     : "memory", "eax" );
}

/* 
 *  run
 *   DESCRIPTION: first parse the command written by ignoring the whitespaces before the actual command and after the actual command
 *                checks if file (comparing all filenames in directory to command) exists in our directories. allocates process number for new process. checks if file is an executable
 *                updates parent esp, ebp and process number into pcb. 
 *   INPUTS: NIL
 *   OUTPUTS: NIL
 *   RETURN VALUE: 0 on success, -1 on failure
 *   SIDE EFFECTS: NIL
 */

uint32_t run(uint8_t* command)
{
    cli();

    if (current_process_num == - 1){ // initialize PIT when the first process is run
        init_pit(PIT_FREQ);
    }

    int i,ch;
    uint8_t fname[FNAME_SIZE];
	dentry_t dentry_list;
	dentry_list.fname = fname;

    /* Begin parsing the command */
    int command_len = strlen((int8_t*)command);
    int start_command = -1;
    for(i=0; i<command_len; i++) // remove trailing spaces
    {
        if(command[i]!=' ')
        {
            start_command = i;
            break;
        }
    }
    int end_command = command_len;
    for(i=start_command; i<command_len; i++) // remove trailing spaces
    {
        if(command[i]==' ')
        {
            end_command = i;
            break;
        }
    }
    ch = 0;

    /* Find command in filesystem */
	for(i = 0; i <fs_meta.tot_directories; i++)
	{
		read_dentry_by_index(i, &dentry_list);

        if (end_command - start_command < strlen((int8_t*)dentry_list.fname)){
            continue;
        }

		if(!strncmp((int8_t*)dentry_list.fname,(int8_t*)command+start_command,end_command-start_command)) // check files for matching command
        {
            ch =1;
            break;
        }
	}
    if(ch==0) // no command found
    {
        sti();
        return -1;
    }


    command[end_command] = '\0'; // parse command
    command = command + start_command;

    /* Bookkeeping information for the parent process, useful for context switching*/
    pcb_t* parent_pcb_ptr;
    if (!is_base_shell  ){ // store the parent's pcb ptr
        parent_pcb_ptr = (pcb_t*) (MB_8 - KB_8 * (current_process_num + 1)); // gets parent pcb ptr
        parent_pcb_ptr->active = 0;
    }
    int32_t parent_process_num = current_process_num; // save current process number to set up PCB

    /* Stores own esp and ebp */
    if (process_bitmask != 0x0){ // stores its own esp and 
        asm volatile("\
            movl %%ebp, %0;\
            movl %%esp, %1\
        "
        : "=r"(get_curr_pcb_ptr()->ebp), "=r"(get_curr_pcb_ptr()->esp)
        : 
        : "eax"
        );
    }

    /* Allocate a new process, changing the process bit vector*/
    if(allocate_process() == -1){
        sti();
        return -1;
    }

    /* Begin reading information from executible file */
    dentry_t dentry;
    read_dentry_by_name(command, &dentry);
    uint32_t fsize = get_size(dentry.inode);

    swap_page(MB_8 + current_process_num * (MB_4)); // swap pages to accomodate child process

    uint8_t* start_address = (uint8_t*)START_ADDR;  // set start address to start of program image 
    read_data(dentry.inode,0,start_address, fsize); // read in data for file

    if (*((uint32_t*)start_address) != MAGIC_NUM){ // check for magic number in file
        parent_pcb_ptr->active = 1;
        swap_page(MB_8);
        deallocate_process();
        sti();
        return -1;
    }

    /* Allocate a PCB for the child processs */
    pcb_t* curr_pcb_ptr = get_curr_pcb_ptr();
    uint32_t parent_esp;
    uint32_t parent_ebp;

    // save current esp and ebp for returning during halt
    asm volatile("\
        movl %%ebp, %0;\
        movl %%esp, %1\
    "
    : "=r"(parent_ebp), "=r"(parent_esp)
    : 
    : "eax"
    );
    curr_pcb_ptr->parent_esp = parent_esp;
    curr_pcb_ptr->parent_ebp = parent_ebp;
    curr_pcb_ptr->active = 1;

    if(is_base_shell)
    {     
        curr_pcb_ptr->parent_process_num = -1;
        is_base_shell = 0;
    }
    else
    {
        curr_pcb_ptr->parent_process_num = parent_process_num;
    }
    

    if (!strncmp((int8_t*)command, "shell", 8)){ // check if a shell is being run
        term_arr[current_term_num]->cursor_position = -1; // initialize a terminal for a struct
        term_arr[current_term_num]->buf_counter = 0;
        term_arr[current_term_num]->length = 0;
        term_arr[current_term_num]->active_process = current_process_num;
        curr_pcb_ptr->term_ptr = term_arr[current_term_num];
        init_buf(curr_pcb_ptr->term_ptr->buf, NUM_COLS * NUM_ROWS); // initialize buffer
        draw_entire_screen(curr_pcb_ptr->term_ptr);
    }
    else{
        curr_pcb_ptr->term_ptr = parent_pcb_ptr->term_ptr;
        curr_pcb_ptr->term_ptr->active_process = current_process_num;
    }

    /* Set up file descriptor array, initializing stdin and stdout */
    for (i = 0; i < MAX_PROCESS; i++){
        if (i == 0 || i == 1) // stdin and stdout
        {
            curr_pcb_ptr->fd_arr[i].flags = 1;
            curr_pcb_ptr->fd_arr[i].file_ops = (i==0)?&stdin_ops:&stdout_ops;
        }
        else{
            curr_pcb_ptr->fd_arr[i].flags = 0;
        }
    }

    /* Store the entry point address, and we begin the switch to user mode */
    uint32_t entry_point = *((uint32_t*)(start_address+ENTRY_POINT_OFFSET));
    switch_to_user_mode(entry_point);

    return 0;
}

/* 
 *  stop
 *   DESCRIPTION: updates PDE (128MB). returns to parent process using parent ebp and esp value. Deallocates current process
 *   INPUTS: NIL
 *   OUTPUTS: NIL
 *   RETURN VALUE: 0
 *   SIDE EFFECTS: NIL
 */

int32_t stop(uint8_t status)
{
    cli();
    pcb_t* curr_pcb_ptr = get_curr_pcb_ptr();
    if (curr_pcb_ptr->parent_process_num != -1){
        pcb_t* parent_pcb_ptr = (pcb_t*) (MB_8 - KB_8 * (curr_pcb_ptr->parent_process_num + 1));
        parent_pcb_ptr->active = 1;
    }

    // perform cleanup
    int8_t parent_process_num = get_curr_pcb_ptr()->parent_process_num;
    get_curr_pcb_ptr()->term_ptr->active_process = parent_process_num;

    tss.esp0 = curr_pcb_ptr->parent_ebp; // restore old stack pointer in TSS
    swap_page(MB_8 + parent_process_num * (MB_4)); 
    uint32_t arg = status & EIGHT_BIT_MASK;

    if (curr_pcb_ptr->parent_process_num == -1){
        if(((terminal_bitmask-1)&(terminal_bitmask))==0) // check if only one terminal is active
        {
            deallocate_process(); // deallocate old process
            is_base_shell  =1;
            run((uint8_t*)"shell");
        }
        else
        {
            terminal_bitmask ^= (1<<current_term_num);
            int i;
            for(i=0; i<NUM_TERM; i++)
            {
                if(terminal_bitmask&(1<<i))
                {
                    process_bitmask ^= (1<<current_process_num); // remove a process via its bitmask
                    term_switch(i);
                }
            }
        }
    }

    /* Close files */
    int i;
    for (i = 0; i < MAX_FD; i++){
        if (curr_pcb_ptr->fd_arr[i].flags) // check if active flag is on
            (*(curr_pcb_ptr->fd_arr[i].file_ops->file_op_ptr[FILE_CLOSE]))(); // close files
    }

    deallocate_process(); // deallocate old process
    asm volatile("\
        movl %2, %%eax; \
        movl %0, %%esp; \
        movl %1, %%ebp; \
        LEAVE; \
        RET; \
    "
    : 
    : "r"(curr_pcb_ptr->parent_esp), "r"(curr_pcb_ptr->parent_ebp), "r"(arg)
    : "ebx"
    );
    return 0;
}

/* 
 *  context_switch
 *   DESCRIPTION: swap pages for new process. updates value in tss to new process
 *   OUTPUTS: NIL
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */

void context_switch(uint8_t new_process_num){

    /* save old ebp and esp value to current pcb */
    cli();
    pcb_t* old_pcb_ptr = get_curr_pcb_ptr();
    asm volatile("\
        movl %%ebp, %0;\
        movl %%esp, %1\
    "
    : "=r"(old_pcb_ptr->ebp), "=r"(old_pcb_ptr->esp)
    : 
    : "eax"
    );
    
    /* change current process to new process num */
    current_process_num = new_process_num;
    pcb_t* new_pcb_ptr = get_curr_pcb_ptr();

    // swap page
    swap_page(MB_8 + current_process_num * (MB_4)); // swap pages to accomodate child process
    if (term_arr[current_term_num]->active_process == current_process_num){
        set_user_vmem ();
    }
    else{
        set_temp_vmem();
    }

    /* perform the context switch, loading old ebp and esp values from the pcb */
    tss.ss0 = KERNEL_DS;
    tss.esp0 = FIRST_ESP - (KB_8 * current_process_num); 
    asm volatile("\
        movl %0, %%esp; \
        movl %1, %%ebp; \
        LEAVE; \
        RET; \
    "
    : 
    : "r"(new_pcb_ptr->esp), "r"(new_pcb_ptr->ebp)
    : "ebx"
    );
}
