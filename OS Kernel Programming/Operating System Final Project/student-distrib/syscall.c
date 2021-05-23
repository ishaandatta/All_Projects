#include "lib.h"
#include "syscall.h"
#include "filesystem.h"
#include "keyboard.h"
#include "i8259.h"
#include "rtc.h"
#include "task.h"
#include "x86_desc.h"
#include "paging.h"
#include "types.h"
#include "terminal.h"

#define MAX_FILES       8
#define INDEX_FIRST_FILE    2
#define VIRTUAL_VIDEO 0x8800000

#define RTC_INODE_VAL -2
#define RTC_STR_LENGTH 3


file_op_table_t file_ops = {{fopen, read_data, fwrite, fclose}};
file_op_table_t rtc_ops = {{rtc_open, rtc_read, rtc_write, rtc_close}};
file_op_table_t dir_ops = {{dir_open, dir_read, dir_write, dir_close}};

/* 
 *  halt
 *   DESCRIPTION: calls helper function stop
 *   INPUTS: status
 *   OUTPUTS: NIL
 *   RETURN VALUE: return result from stop (0)
 *   SIDE EFFECTS: NIL
 */

int32_t halt(uint8_t status){
    return stop(status);
}

/* 
 *  execute
 *   DESCRIPTION: calls helper function run
 *   INPUTS: command
 *   OUTPUTS: NIL
 *   RETURN VALUE: return result from run (0 on success, -1 on failure)
 *   SIDE EFFECTS: NIL
 */

int32_t execute(const uint8_t* command){
    if (command == NULL ||process_bitmask == EIGHT_BIT_MASK){
        return -1;
    }
    uint8_t command_dup[MAX_BUFF_SIZE];
    strcpy((int8_t*)command_dup, (int8_t*)command);
    return run(command_dup);
}

/* 
 *  read
 *   DESCRIPTION: checks if fd is within range (1 to 7). if fd == 0 (stdin), call function term_read. If it is a rtc file calling read, call fuction rtc_read. 
 *                if it's a file, call function read_data, and update file_position for that file by the length read.
 *   INPUTS: command
 *   OUTPUTS: NIL
 *   RETURN VALUE: -1 if file is not supposed to read and return value from function (term_read or rtc_read or read_data)
 *   SIDE EFFECTS: NIL
 */

int32_t read (int32_t fd, void* buf, int32_t nbytes)
{
    if (fd < 0 || fd > MAX_FILES - 1 || fd == 1 || buf == NULL){
        return -1;
    }
    pcb_t* curr_pcb_ptr = get_curr_pcb_ptr();
    if (fd == 0)
    { 
        // stdin
        return (*(curr_pcb_ptr->fd_arr[fd].file_ops->file_op_ptr[FILE_READ]))((uint8_t*)buf, nbytes);
    }
    if (curr_pcb_ptr->fd_arr[fd].inode == RTC_INODE_VAL)
    {
         // rtc
        return (*(curr_pcb_ptr->fd_arr[fd].file_ops->file_op_ptr[FILE_READ]))(); 
    }
    else { //filesystem read
        if(curr_pcb_ptr->fd_arr[fd].flags==0){
            return -1;
        }

        if(curr_pcb_ptr->fd_arr[fd].inode==-1)
        {
            int toRet = (*(curr_pcb_ptr->fd_arr[fd].file_ops->file_op_ptr[FILE_READ]))((uint8_t*) buf, curr_pcb_ptr->fd_arr[fd].file_position); // jumps to read function
            curr_pcb_ptr->fd_arr[fd].file_position++;
            return toRet;
        }
        else
        {
            int toRet = (*(curr_pcb_ptr->fd_arr[fd].file_ops->file_op_ptr[FILE_READ]))(curr_pcb_ptr->fd_arr[fd].inode, curr_pcb_ptr->fd_arr[fd].file_position, (uint8_t*)buf,nbytes); // jumps to read function
            curr_pcb_ptr->fd_arr[fd].file_position+=toRet;
            return toRet;
        }
    }
    return -1;
}

/* 
 *  write
 *   DESCRIPTION: checks if fd is within range (1 to 7). if fd == 1 (stdout), call function term_write. If it is a rtc file calling write,, call fuction rtc_write. if it's neither stdout or rtc, return - 1
 *   INPUTS: command
 *   OUTPUTS: NIL
 *   RETURN VALUE: -1 if file is not supposed to write and return value from function (term_write or rtc_write)
 *   SIDE EFFECTS: NIL
 */

int32_t write (int32_t fd, const void* buf, int32_t nbytes){
    if (fd < 0 || fd > MAX_FILES - 1 || fd == 0 || buf == NULL){
        return -1;
    }
    
    pcb_t* curr_pcb_ptr = get_curr_pcb_ptr();
    if(fd == 1)
    {
        // stdout
        return (*(curr_pcb_ptr->fd_arr[fd].file_ops->file_op_ptr[FILE_WRITE]))((uint8_t*)buf, nbytes);
    }
    if(curr_pcb_ptr->fd_arr[fd].inode == RTC_INODE_VAL){ // rtc
        return (*(curr_pcb_ptr->fd_arr[fd].file_ops->file_op_ptr[FILE_WRITE]))(buf); 
    }
    return -1;
}

/* 
 *  open
 *   DESCRIPTION: In the current process, open the file given in the argument. If more than 8 files opened, open will fail and reutrn -1. Depending on what type of file is being opened,
 *                the elements in the file operation array will contain the respective open read write close function. (i.e. if rtc. file open will be rtc_open). inode will be set to -2
 *                for rtc, -1 for directory and dentry inode for usual file. 
 *   INPUTS: filename
 *   OUTPUTS: flags = 1
 *            inode: -2 (rtc), -1 (directory), dentry.inode(normal file)
 *            file_op_ptr[rtc_open,rtc_read,rtc_write,rtc_close] (rtc), file_op_ptr[dir_open,dir_read,dir_write,dir_close] (directory), file_op_ptr[f_open,read_data,f_write,f_close] (normal files)
 *            file_position: 0
 *   RETURN VALUE: file descriptor (index into array) if it works and -1 if it fails
 *   SIDE EFFECTS: NIL
 */

int32_t open (const uint8_t* filename){
    int i;
    if (filename == NULL){
        return -1;
    }
    if (!strncmp((int8_t*)filename, (int8_t*)"rtc", RTC_STR_LENGTH)){
        for (i = INDEX_FIRST_FILE; i < MAX_FILES; i++){
            pcb_t* curr_pcb_ptr = get_curr_pcb_ptr();
            if (curr_pcb_ptr->fd_arr[i].flags == 0){
                curr_pcb_ptr->fd_arr[i].flags = 1; // mark as used

                curr_pcb_ptr->fd_arr[i].file_ops = &rtc_ops;
                curr_pcb_ptr->fd_arr[i].inode  = RTC_INODE_VAL; // note that we are using -2 for the rtc inode value
                curr_pcb_ptr->fd_arr[i].file_position = 0; // initialize file position
                return i;
            }
        }
    }
    if (*filename == '.'){ // reading a directories (eg. in ls)
        for (i = INDEX_FIRST_FILE; i < MAX_FILES; i++){
            pcb_t* curr_pcb_ptr = get_curr_pcb_ptr();
            if (curr_pcb_ptr->fd_arr[i].flags == 0){
                curr_pcb_ptr->fd_arr[i].flags = 1; // mark as used

                curr_pcb_ptr->fd_arr[i].file_ops = &dir_ops;
                curr_pcb_ptr->fd_arr[i].inode  =-1; // note that we are using -2 for the dir inode value
                curr_pcb_ptr->fd_arr[i].file_position = 0; // initialize file position
                return i;
            }
        }
    }
    else
    {
        dentry_t dentry;
        uint8_t fname[FNAME_SIZE+1];
        uint8_t fname_dup[FNAME_SIZE+1];
        strcpy((int8_t*)fname_dup, (int8_t*)filename);
        dentry.fname = fname;
        if(read_dentry_by_name(fname_dup, &dentry))
        {
            return -1;
        }
        for (i = INDEX_FIRST_FILE; i < MAX_FILES; i++){
            pcb_t* curr_pcb_ptr = get_curr_pcb_ptr();
            if (curr_pcb_ptr->fd_arr[i].flags == 0){
                curr_pcb_ptr->fd_arr[i].flags = 1; // mark as used

                curr_pcb_ptr->fd_arr[i].file_ops = &file_ops;
                curr_pcb_ptr->fd_arr[i].inode = dentry.inode;
                curr_pcb_ptr->fd_arr[i].file_position = 0; // initialize file position
                return i;
            }
        }
    }
    return -1;
}
/* 
 *   close
 *   DESCRIPTION: closes the file that is currently open. checks if the value of file descriptor is between 2 to 7 (inclusive), return -1 if it's not. if the file you're trying to 
 *                close is a rtc file, disable irq(8). set flag for file descriptor to 0
 *   INPUTS: fd (index into array)
 *   OUTPUTS: flags for the file being closed to be set to 0
 *            if file is rtc, disable interrupt 8
 *   RETURN VALUE: -1 on failure and 0 for succeed
 *   SIDE EFFECTS: NIL
 */

int32_t close(int32_t fd){
    if (fd < INDEX_FIRST_FILE || fd > MAX_FILES - 1){
        return -1;
    }
    pcb_t* curr_pcb_ptr = get_curr_pcb_ptr();
    if (curr_pcb_ptr->fd_arr[fd].inode == RTC_INODE_VAL){
        disable_irq(RTC_IRQ);
    }
    if (curr_pcb_ptr->fd_arr[fd].flags == 1){
        // return (curr_pcb_ptr->fd_arr[fd].flags = 0);
        curr_pcb_ptr->fd_arr[fd].flags = 0;
        return (*(curr_pcb_ptr->fd_arr[fd].file_ops->file_op_ptr[FILE_CLOSE]))(); 
    }
    return -1;
}

/* 
 *   getargs
 *   DESCRIPTION: reads the program's command line arguments into user level buffer
 *   INPUTS: buf, nbytes
 *   OUTPUTS: 
 *   RETURN VALUE: -1 on failure and 0 for succeed
 *   SIDE EFFECTS: NIL
 */

int32_t getargs(uint8_t* buf, int32_t nbytes){
    if (buf == NULL || nbytes == 0){ // check for error values
        return -1;
    }
    return term_getargs(buf, nbytes);
}

/* 
 *   vidmap
 *   DESCRIPTION: remaps video memory to user space
 *   INPUTS: 
 *   OUTPUTS:  
 *   RETURN VALUE: -1 on failure and 0 for succeed
 *   SIDE EFFECTS: NIL
 */

int32_t vidmap(uint8_t** screen_start){
    if ((uint32_t)screen_start == NULL || (uint32_t)screen_start > USER_VIRTUAL_END_ADDR - 1 || (uint32_t)screen_start < USER_VIRTUAL_START_ADDR){
        return -1;
    }
    *screen_start = (uint8_t*)VIRTUAL_VIDEO;
    set_user_vmem();
    return VIRTUAL_VIDEO;
}

/* 
 *   set_handler
 *   DESCRIPTION: NIL
 *   INPUTS: 
 *   OUTPUTS:  
 *   RETURN VALUE: -1
 *   SIDE EFFECTS: NIL
 */

int32_t set_handler(int32_t signum, void* handler_address){
    return -1;
}

/* 
 *   sigreturn
 *   DESCRIPTION: NIL
 *   INPUTS: 
 *   OUTPUTS:  
 *   RETURN VALUE: -1 
 *   SIDE EFFECTS: NIL
 */

int32_t sigreturn(){
    return -1;
}
