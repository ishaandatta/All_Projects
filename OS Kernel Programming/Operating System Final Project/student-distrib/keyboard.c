#include "i8259.h"
#include "lib.h"
#include "keyboard.h"
#include "syscall.h"
#include "task.h"
#include "terminal.h"
#include "types.h"

#define MAX_SCANCODE    58

uint8_t control_state = 0;
uint8_t caps_state = 0;
uint8_t shift_state = 0;
uint8_t alt_state = 0;

// static char* video_mem = (char *)VIDEO;

// volatile uint8_t enter_flag = 0;
volatile uint8_t video_mem_lock = 0;
// volatile uint8_t read_flag = 0;

uint8_t curr_term;

// adapted from http://www.cs.umd.edu/~hollings/cs412/s98/project/proj1/scancode
char asccode[MAX_SCANCODE][2] =       /* Array containing ascii codes for
                appropriate scan codes */
    {
    {   0,0   } ,
    { 0,0 } ,
    { '1','!' } ,
    { '2','@' } ,
    { '3','#' } ,
    { '4','$' } ,
    { '5','%' } ,
    { '6','^' } ,
    { '7','&' } ,
    { '8','*' } ,
    { '9','(' } ,
    { '0',')' } ,
    { '-','_' } ,
    { '=','+' } ,
    {   0,0   } ,
    {   0,0   } ,
    { 'q','Q' } ,
    { 'w','W' } ,
    { 'e','E' } ,
    { 'r','R' } ,
    { 't','T' } ,
    { 'y','Y' } ,
    { 'u','U' } ,
    { 'i','I' } ,
    { 'o','O' } ,
    { 'p','P' } ,
    { '[','{' } ,
    { ']','}' } ,
    {  0,0  } ,
    {   0,0   } ,
    { 'a','A' } ,
    { 's','S' } ,
    { 'd','D' } ,
    { 'f','F' } ,
    { 'g','G' } ,
    { 'h','H' } ,
    { 'j','J' } ,
    { 'k','K' } ,
    { 'l','L' } ,
    { ';',':' } ,
    {  '\'','\"'  } ,
    { '`','~' } ,
    {    0,0   } ,
    { '\\','|'} ,
    { 'z','Z' } ,
    { 'x','X' } ,
    { 'c','C' } ,
    { 'v','V' } ,
    { 'b','B' } ,
    { 'n','N' } ,
    { 'm','M' } ,
    { ',','<' } ,
    { '.','>' } ,
    { '/','?' } ,
    {   0,0   } ,
    {   0,0   } ,
    {   0,0   } ,
    { ' ',' ' } ,
};

/* 
 *  keyboard_init
 *   DESCRIPTION: Initializes keyboard, setting the cursor to the start, and enabling kb interrupts
 *   INPUTS: NIL
 *   OUTPUTS: NIL
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */
void keyboard_init(){
    enable_irq(1); // enable the keyboard irq line
    screen_y = 0;
    screen_x = 0;
    update_cursor (screen_x, screen_y);
}

/* 
 *  keyboard_display
 *   DESCRIPTION: Display a user-pressed key to the screen (if applicable), unknown scancodes are ignored
 *  function also handles caps lock, shift, and special characters
 *   INPUTS: NIL
 *   OUTPUTS: NIL
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */
void keyboard_display(){
    cli();
    uint8_t scancode = inb(0x60);
    pcb_t* curr_pcb_ptr = get_curr_pcb_ptr();
    if (scancode < MAX_SCANCODE && asccode[scancode][0] != 0){
        if(term_arr[current_term_num]->limit < CHAR_LIMIT){
            if (asccode[scancode][0] >= 'a' && asccode[scancode][0] <= 'z'){ // check alphabets
                if (asccode[scancode][0] == 'l' && control_state){ // check control-L
                    init_buf(curr_pcb_ptr->term_ptr->buf, VID_BUF_SIZE);
                    curr_pcb_ptr->term_ptr->length = 0;
                    curr_pcb_ptr->term_ptr->cursor_position = 0;
                    draw_entire_screen(term_arr[current_term_num]);
                    if (term_arr[current_term_num]->read_flag){
                        // curr_pcb_ptr->term_ptr->buf_counter = -1; // reset the buffer
                        curr_pcb_ptr->term_ptr->buf_counter = 0; // reset the buffer

                    }
                }
                else{
                    term_arr[current_term_num]->limit++; 
                    write_buf(term_arr[current_term_num], asccode[scancode][caps_state ^ shift_state]);
                }
            }
            else { // number is pressed
                term_arr[current_term_num]->limit++; 
                write_buf(term_arr[current_term_num], asccode[scancode][shift_state]);
            }
            

            if (term_arr[current_term_num]->read_flag && term_arr[current_term_num]->buf_counter < MAX_BUFF_SIZE){ // if read is enabled, keep track of the characters typed to a buffer
                // term_buf[current_term_num][curr_pcb_ptr->term_ptr->buf_counter] = asccode[scancode][caps_state ^ shift_state];
                term_arr[current_term_num]->term_buf[term_arr[current_term_num]->buf_counter] = asccode[scancode][caps_state ^ shift_state];
                term_arr[current_term_num]->buf_counter++;
            }
            if (term_arr[current_term_num]->length == VID_BUF_SIZE){  // detect end of line
                term_scroll(term_arr[current_term_num]);
            }
        }
    }


    if (scancode == 0x3a){  // caps lock pressed
        caps_state = !caps_state;
    }

    else if (scancode >= 0x3b && scancode <= 0x3d){ // function keys pressed 
        term_switch(scancode - 0x3b); // switch to the correct terminal
    }

    else if (scancode == 0xaa){ // left shift released
        shift_state = 0;
    }
    else if (scancode == 0x2a){ // left shift pressed
        shift_state = 1;
    } 
    else if (scancode == 0xb8){ // left alt released
        alt_state = 0;
    }
    else if (scancode == 0x28){ // left alt pressed
        alt_state = 1;
    } 
    else if (scancode == 0x1c) {// enter key pressed
        term_arr[current_term_num]->enter_flag = 1;
        term_arr[current_term_num]->limit = 0;
        term_scroll(term_arr[current_term_num]);
        // curr_pcb_ptr->term_ptr->del_limit = curr_pcb_ptr->term_ptr->length;
        term_arr[current_term_num]->del_limit = term_arr[current_term_num]->length;
    }

    else if (scancode == 0xe){ // backspace
        if(term_arr[current_term_num]->limit != 0) {
            term_arr[current_term_num]->limit--;
        }
        if (term_arr[current_term_num]->del_limit < term_arr[current_term_num]->length){
            delete_char(term_arr[current_term_num]);
        }
    }

    else if (scancode == 0x9d){ // ctrl pressed
        control_state = 0;
    }
    else if (scancode == 0x1d){ // ctrl released
        control_state = 1;
    }
    draw_screen(term_arr[current_term_num]);
}

