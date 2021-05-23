
// volatile extern uint8_t enter_flag;

// volatile extern uint8_t read_flag;

volatile extern uint8_t video_mem_lock;

 // buffer holding the current terminal cmd
extern uint8_t curr_term;

void keyboard_init();
void keyboard_display();


