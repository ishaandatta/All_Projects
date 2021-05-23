#include "types.h"

void draw_screen(term_t*  curr_term_ptr);
void write_buf(term_t*  curr_term_ptr, char c);

int32_t term_read(uint8_t* buf, int32_t nbytes);
int32_t term_write(uint8_t* buf, int32_t nbytes);
int32_t term_open();
int32_t term_close();
int32_t term_invalid();
int32_t term_driver (uint8_t cmd, uint8_t* buf, int32_t nbytes);

void handle_newline();
void term_scroll();
void clear_row(term_t*  curr_term_ptr);
void delete_char();
void update_cursor (uint32_t cursor_x, uint32_t cursor_y);
void write_vmem(uint32_t offset, char c);
void write_buf(term_t*  curr_term_ptr, char c);

void term_scroll(term_t*  curr_term_ptr);

void term_driver_int(uint8_t cmd, uint32_t num);

void draw_entire_screen(term_t*  curr_term_ptr);

void init_buf(char* buf, int nbytes);

void term_switch(uint8_t new_term_num);

extern uint8_t is_base_shell;
int32_t term_getargs(uint8_t* buf, int32_t nbytes);
