#define MAX_PROCESS 8


typedef struct file_op_table {
    int32_t (*file_op_ptr[4])();
} file_op_table_t;


typedef struct fd_entry {
    file_op_table_t* file_ops;
    int32_t inode; // inode of file, -1 for directory, -2 for rtc
    uint32_t file_position; // shows the current position in the file that the user is reading
    uint32_t flags; // 1 if in use, 0 if not
} fd_entry_t;

typedef struct term{
    int32_t cursor_position; // last position that has been written to vmem
    int32_t length; // index into buffer
    uint32_t buf_counter;
    uint32_t del_limit;
    volatile uint8_t read_flag;
    volatile uint8_t enter_flag;
    uint32_t limit;

    int8_t active_process; // current active process associated with the terminal (shell by p_num by default)
    
    char buf[NUM_COLS * NUM_ROWS]; // buffer to write into vmem

    char term_buf[MAX_BUFF_SIZE];
} term_t;

typedef struct pcb{
    uint8_t active; // determines if the process is active and should receive scheduling time
    uint32_t parent_esp; // stores the esp and ebp of parent. used when halting to parent
    uint32_t parent_ebp;
    uint32_t esp; // stores the current esp and ebp. used when context switching during scheduling
    uint32_t ebp;
    int8_t parent_process_num; // stores the process number of the parent
    fd_entry_t fd_arr[8];     // file descripor array
    term_t* term_ptr; // pointer to terminal struct associated with the process
} pcb_t;



uint32_t run(uint8_t* command);
void switch_to_user_mode(uint32_t entry_point);
pcb_t* get_curr_pcb_ptr();

// pcb_t* process_table[MAX_PROCESS];  

extern int p_num;

extern pcb_t* curr_pcb_ptr;
extern uint32_t process_bitmask;

extern uint8_t terminal_bitmask;
extern int32_t current_process_num;
extern int32_t current_term_num;
extern term_t* term_arr[3];

pcb_t* get_curr_pcb_ptr();
uint32_t allocate_process();
void deallocate_process();
void switch_to_user_mode(uint32_t entry_point);
uint32_t run(uint8_t* command);
int32_t stop(uint8_t status);

void context_switch(uint8_t new_process_num);

