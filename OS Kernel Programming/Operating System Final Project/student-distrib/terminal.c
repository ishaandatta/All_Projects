#include "i8259.h"
#include "lib.h"
#include "keyboard.h"
#include "syscall.h"
#include "task.h"
#include "terminal.h"
#include "types.h"

#define CHAR_ATTRIB_SIZE 2
#define MAX_SIZE 1024
#define SECOND_ROW_OFFSET 2
#define CURSOR_X_PORT 0x000E
#define CURSOR_Y_PORT 0x000F
#define HIGH_EIGHT_BITS 8
#define CURSOR_PORT 0x03D4
#define NUMBER_OF_VALUES 2



static char* video_mem = (char *)VIDEO;
uint8_t is_base_shell = 1;

/* 
 *  draw_screen
 *   DESCRIPTION:  if length(term_t) is less than cursor position call write_vmem and fill it with ' '. if not, fill it with whatever is in buf(term_t)
 *   INPUTS: curr_term_ptr (pointer to whichever term_t user is typing in)
 *   OUTPUTS: NIL
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */

void draw_screen(term_t*  curr_term_ptr){
    int i;
    if (curr_term_ptr->length <= curr_term_ptr->cursor_position){
        for (i = curr_term_ptr->length; i <= curr_term_ptr->cursor_position; i++){
            write_vmem(i, ' ');
            curr_term_ptr->buf[i] = ' ';
        }
    }
    else{
        for (i = curr_term_ptr->cursor_position + 1; i < curr_term_ptr->length; i++){
            write_vmem(i, curr_term_ptr->buf[i]);
        }
    }
    curr_term_ptr->cursor_position = curr_term_ptr->length - 1;
    update_cursor(curr_term_ptr->cursor_position % NUM_COLS + 1, curr_term_ptr->cursor_position/NUM_COLS);
}



/* 
 *  draw_entire_screen
 *   DESCRIPTION:  this function draws the entire screen, regardless of the length and cursor position values. This is only called in term_scroll, where we want to redraw the entire screen,
 *                 but still keep the length and cursor_position variables
 *   INPUTS: curr_term_ptr (pointer to whichever term_t user is typing in)
 *   OUTPUTS: NIL
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */
void draw_entire_screen(term_t*  curr_term_ptr){
    int i;
    for (i = 0; i < VID_BUF_SIZE; i++){
        write_vmem(i, curr_term_ptr->buf[i]);
    }
}

/* 
 *  write_vmem
 *   DESCRIPTION:  write one character to the screen
 *   INPUTS: uint32_t offset, char c
 *   OUTPUTS: NIL
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */
void write_vmem(uint32_t offset, char c){
    *(uint8_t*)(video_mem + (offset * CHAR_ATTRIB_SIZE))  = c;
    *(uint8_t*)(video_mem + (offset * CHAR_ATTRIB_SIZE + 1))  = ATTRIB;
}

/* 
 *  write_buf
 *   DESCRIPTION:  writes one character to the buffer (term_t struct) and updates length (term_t struct)
 *   INPUTS: term_t*  curr_term_ptr, char c
 *   OUTPUTS: NIL
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */
void write_buf(term_t*  curr_term_ptr, char c){
    curr_term_ptr->buf[curr_term_ptr->length] = c;
    curr_term_ptr->length++;
}

/* 
 *  term_read
 *   DESCRIPTION: sets read_flag to be 1 so that term_buf can be updated. number of chars to be stored is min(nbytes,buf_counter) after enter has been pressed. updates buf with everything
 *                user has typed (in term_buf) after read_flag has changed
 *   INPUTS: uint8_t* buf, int32_t nbytes
 *   OUTPUTS: NIL
 *   RETURN VALUE: limit + 1 (number of chars read + 1)
 *   SIDE EFFECTS: NIL
 */

int32_t term_read(uint8_t* buf, int32_t nbytes){
    sti();
    if (nbytes > 1024 || buf == NULL){
        return -1;
    }
    uint32_t i;
    uint8_t* toWrite = (uint8_t*)buf;
    int limit;
    pcb_t* curr_pcb_ptr = get_curr_pcb_ptr();

    curr_pcb_ptr->term_ptr->buf_counter = 0;
    curr_pcb_ptr->term_ptr->read_flag = 1;
    while (!curr_pcb_ptr->term_ptr->enter_flag){;} // spin until enter key is received form keyboard
    limit = term_arr[current_term_num]->buf_counter < nbytes ? term_arr[current_term_num]->buf_counter : nbytes;

    for (i = 0; i < limit ; i++) {
        toWrite[i] =  term_arr[current_term_num]->term_buf[i]; // save terminal buffer to write buffer
    }

    toWrite[limit] = '\n';
    term_arr[current_term_num]->term_buf[limit] = '\n';

    term_arr[current_term_num]->enter_flag = 0;
    term_arr[current_term_num]->read_flag = 0; // done reading

    return limit + 1;
}

/* 
 *  term_write
 *   DESCRIPTION: for each char in input buf call write_buf to store into term_t buf. if it's handle carriage, ignore it. if it's handle newline, call term_scroll. then call draw_scree to update
 *                screen with whatever's in buf
 *   INPUTS: uint8_t* buf, int32_t nbytes
 *   OUTPUTS: NIL
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */

int32_t term_write(uint8_t* buf, int32_t nbytes){
    uint32_t i;
    uint8_t* toWrite = (uint8_t*)buf;
    pcb_t* curr_pcb_ptr = get_curr_pcb_ptr();
    if (nbytes > MAX_SIZE || buf == NULL){
        return -1;
    }
    for(i = 0; i < nbytes; i++){
        if (toWrite[i] == '\n'){ // handle  newline (\n)
            term_scroll(curr_pcb_ptr->term_ptr);
            continue;
        }
        if (toWrite[i] == '\r') { // handle carraige return (\r)
            // curr_pcb_ptr->term_ptr->cursor_position  = (curr_pcb_ptr->term_ptr->cursor_position / NUM_COLS) * NUM_COLS;
            continue;
        }
        write_buf(curr_pcb_ptr->term_ptr, toWrite[i]);
        if (curr_pcb_ptr->term_ptr->length % NUM_COLS == 0 && curr_pcb_ptr->term_ptr->cursor_position != 0 && curr_pcb_ptr->term_ptr->length / NUM_COLS >= NUM_ROWS - 1){  // detect end of line
                term_scroll(curr_pcb_ptr->term_ptr);
        }
    }
    if (curr_pcb_ptr->term_ptr == term_arr[current_term_num]) 
    {
        draw_screen(curr_pcb_ptr->term_ptr);   
    }
    curr_pcb_ptr->term_ptr->del_limit = curr_pcb_ptr->term_ptr->length; 
    return nbytes;
}


/* 
 *  term_open
 *   DESCRIPTION: nothing
 *   INPUTS: NIL
 *   OUTPUTS: NIL
 *   RETURN VALUE: 0 
 *   SIDE EFFECTS: NIL
 */
int32_t term_open(){
    return 0; // dummy function
}

/* 
 *  term_close
 *   DESCRIPTION: nothing
 *   INPUTS: NIL
 *   OUTPUTS: NIL
 *   RETURN VALUE: 0 
 *   SIDE EFFECTS: NIL
 */
int32_t term_close(){
    return 0; // dummy function
}

/* 
 *  term_invalid
 *   DESCRIPTION: nothing
 *   INPUTS: NIL
 *   OUTPUTS: NIL
 *   RETURN VALUE: -1 
 *   SIDE EFFECTS: NIL
 */
int32_t term_invalid()
{
    return -1;
}

/* 
 *  handle_newline
 *   DESCRIPTION: Handles a newline input, either triggered by the user pressing enter, or with the cursor reaching
 *  the end of line
 *   INPUTS: NIL
 *   OUTPUTS: NIL
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */
void handle_newline(){
    pcb_t* curr_pcb_ptr = get_curr_pcb_ptr();
    term_scroll(curr_pcb_ptr->term_ptr);
    screen_x = 0;
    update_cursor(screen_x, screen_y);
}

/* 
 *  term_scroll
 *   DESCRIPTION: Handles scrolling of the terminal. Will also scroll up the whole screen when reaching the bottom line
 *   INPUTS: NIL
 *   OUTPUTS: NIL
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */
void term_scroll(term_t*  curr_term_ptr){
    int i;
    if (curr_term_ptr->length / NUM_COLS >= NUM_ROWS - 1){
        for (i = SECOND_ROW_OFFSET; i < NUM_ROWS + 1; i++){
            memcpy((uint8_t *)(curr_term_ptr->buf + ((NUM_COLS * (i - SECOND_ROW_OFFSET)))), (uint8_t *)(curr_term_ptr->buf + ((NUM_COLS * (i - 1)))), NUM_COLS); // copes i-2 row into i-1 row
        }

        curr_term_ptr->del_limit -= NUM_COLS;
        // screen_y = NUM_ROWS - 1;
        // screen_x = 0;
        curr_term_ptr->cursor_position = (NUM_ROWS - 1) * NUM_COLS - 1;
        curr_term_ptr->length = (NUM_ROWS - 1) * NUM_COLS;
        for (i = (NUM_ROWS - 1)* NUM_COLS; i < NUM_ROWS* NUM_COLS; i++){ // clears last row
            curr_term_ptr->buf[i] = ' ';
        }
        if (curr_term_ptr == term_arr[current_term_num]) 
        {
            draw_entire_screen(term_arr[current_term_num]);
        }
    }
    else {
        // screen_y++;
        curr_term_ptr->length += NUM_COLS;
        curr_term_ptr->length = (curr_term_ptr->length / NUM_COLS )* NUM_COLS;
    }
}

/* 
 *   delete_char
 *   DESCRIPTION: Handles the deleting of characters from the terminal (backspace). Note, the del_limit specifies the 
 *   limit in which backspace should work. This limit is resetted each time the user press enter, or a terminal write function
 *   is called.
 *   INPUTS: NIL
 *   OUTPUTS: NIL
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */
void delete_char(term_t*  curr_term_ptr){
    curr_term_ptr->length--;
    if (term_arr[current_term_num]->read_flag){
        term_arr[current_term_num]->buf_counter--;
    }
}

/* 
 *   update_cursor
 *   DESCRIPTION: Updates the cursor value to the screen. This is done by manipulated VGA registers
 *   INPUTS: x coordinate of cursor
 *              y coordinate of cursor
 *   OUTPUTS: NIL
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */
void update_cursor (uint32_t cursor_x, uint32_t cursor_y){
    uint16_t text_CRTC[2] = {
         CURSOR_X_PORT, CURSOR_Y_PORT   // 0x0E and 0x0F are the repsective x and y port numbers to control the cursor position
    };
    // 0x0e is the cursor high register, 0x0f is the cursor low register
    uint16_t offset = cursor_x + (cursor_y * NUM_COLS);
    text_CRTC[0] |= (offset & EIGHT_TO_FIFTEEN_MASK);
    text_CRTC[1] |= (offset & EIGHT_BIT_MASK) << HIGH_EIGHT_BITS;
    rep_outsw (CURSOR_PORT, text_CRTC, NUMBER_OF_VALUES); // update cursor location to the respective port 
}   

/* 
 *   init_buf
 *   DESCRIPTION: Updates the cursor value to the screen. This is done by manipulated VGA registers
 *   INPUTS: buf (array of chars to be cleared) nbytes (size of array buf)
 *   OUTPUTS: buf of size nbytes to be filled with ' '
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */

void init_buf(char* buf, int nbytes){
    int i;
    for (i = 0; i < nbytes; i++){
        buf[i] = ' '; 
    }
}

/* 
 *   term_switch
 *   DESCRIPTION: changes terminal based on input new_term_num. allocates new terminal if it has not been allocated. if not, execute context switch. draw_entire_screen based on new terminal's buf
 *   INPUTS: new term num
 *   OUTPUTS: output new terminal's buf onto screen
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */

void term_switch(uint8_t new_term_num){
    if (process_bitmask == EIGHT_BIT_MASK && new_term_num != current_term_num){
        // term_write("\nMax Number of Processes Reached!", strlen("\nMax Number of Processes Reached!"));
        term_write((uint8_t*)"\nMax Number of Processes Reached!", (int32_t)strlen("\nMax Number of Processes Reached!"));
        return;
    }
    cli();
    if (new_term_num == current_term_num){ // new terminal is already active, no need to switch
        sti();
        return;
    }
    if ((terminal_bitmask & (1 << new_term_num)) == 0){ // allocate a new terminal
        current_term_num = new_term_num;
        terminal_bitmask |= (0x1 << new_term_num);
        is_base_shell = 1;
        run((uint8_t*)"shell");
    }
    else{
        current_term_num = new_term_num;
        draw_entire_screen(term_arr[current_term_num]);
        context_switch(term_arr[current_term_num]->active_process); // switch to process of new terminal
    }
}

/* 
 *   term_getargs
 *   DESCRIPTION: gets argument based on user input
 *   INPUTS: buffer to fill, number of bytes to fill
 *   OUTPUTS: output new terminal's buf onto screen
 *   RETURN VALUE: NIL
 *   SIDE EFFECTS: NIL
 */
int32_t term_getargs(uint8_t* buf, int32_t nbytes){
    // char* input_buf = term_arr[curr_term]->term_buf;
        char* input_buf = get_curr_pcb_ptr()->term_ptr->term_buf;

    int i = 0; // index into terminal buffer
    int j = 0; // index into output buffer
    while (input_buf[i] == ' '){ // find command
        i++;
    }
    while (input_buf[i] != ' '){ // find space
        if (input_buf[i] == '\n'){
            return -1;
        }
        i++;
    }
    while (input_buf[i] == ' '){ // find argument
        i++;
    }
    if (i > nbytes){ // check for overflow
        buf[0] = '\0';
        return -1;
    }
    while (input_buf[i] != '\n' && j < nbytes){
        buf[j] = input_buf[i];
        j++;
        i++;
    }
    buf[j] = '\0';
    if (j == 0){
        return -1;
    }
    return 0;
}
