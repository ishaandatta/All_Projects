#include "tests.h"
#include "x86_desc.h"
#include "lib.h"
#include "idt.h"
#include "i8259.h"
#include "paging.h"
#include "isr.h"
#include "filesystem.h"
#include "rtc.h"

#define PASS 1
#define FAIL 0

// #define CP1_TESTS
// #define CP2_TESTS

/* format these macros as you see fit */
#define TEST_HEADER 	\
	printf("[TEST %s] Running %s at %s:%d\n", __FUNCTION__, __FUNCTION__, __FILE__, __LINE__)
#define TEST_OUTPUT(name, result) \
	print_test_output(name,result);

static inline void assertion_failure(){
	/* Use exception #15 for assertions, otherwise
	   reserved by Intel */
	asm volatile("int $15");
}


// void print_test_output(uint8_t* name, uint32_t (*result)() )
// {
// 	term_driver(1,(uint8_t*)"[TEST] ", strlen((int8_t*)"[TEST] "));
// 	term_driver(1,(uint8_t*)name, strlen((int8_t*)name));
// 	if ((uint32_t)result == PASS){
// 		term_driver(1, (uint8_t*)" Result = PASS\n", strlen((int8_t*)" Result = PASS\n"));
// 	}
// 	else{
// 		term_driver(1, (uint8_t*)" Result = FAIL\n", strlen((int8_t*)" Result = FAIL\n"));
// 	}
// }
/* Checkpoint 1 tests */

/* IDT Test - Example
 *
 * Asserts that first 10 IDT entries are not NULL
 * Inputs: None
 * Outputs: PASS/FAIL
 * Side Effects: None
 * Coverage: Load IDT, IDT definition
 * Files: x86_desc.h/S
 */

#ifdef CP1_TESTS
int idt_test(){
	TEST_HEADER;

	int i;
	int result = PASS;
	for (i = 0; i < 10; ++i){
		if ((idt[i].offset_15_00 == NULL) &&
			(idt[i].offset_31_16 == NULL)){
			assertion_failure();
			result = FAIL;
		}
	}

	return result;
}

/* IDT Entries test
 *
 * Ensures that the first 32 entries of the idt are set correctly (i.e. segment selector == kernel_cs, reserved 4 == 0)
 * Inputs: None
 * Outputs: PASS/FAIL
 * Side Effects: None
 * Coverage: Ensures all 32 entries are filled up as intended
 * Files: idt.c
 */

int idt_entry_test(){
	TEST_HEADER;

	int i;
	int result = PASS;
	// check first 32 entries of the idt
	for (i = 0; i < 32; i++){
		void* isr_pointer = (void*)((idt[i].offset_15_00) | (idt[i].offset_31_16 << 16)); // get function pointer entry from the idt
		// perform comparison to expected values
		if (isr_pointer != (void *)isr_arr[i] ||
		idt[i].seg_selector != KERNEL_CS ||
        idt[i].reserved4 != 0 ||
        idt[i].reserved3 != 1 ||
        idt[i].reserved2 != 1 ||
        idt[i].reserved1 != 1 ||
        idt[i].size != 1 ||
        idt[i].reserved0 != 0 ||
        idt[i].dpl != 0 ||
        idt[i].present != 1){
			assertion_failure(); // failure should generate an exception
			result = FAIL;
		}
	}
	return result;
}

/* Page Fault test
 *
 * Ensures that the memory address associated with the page range determined by the PTE and PDE has present bit set to 1 -> no page fault
 * Inputs: None
 * Outputs: PASS/FAIL
 * Side Effects: None
 * Coverage: Ensures that the memory address associated in the PTE and PDE has present bit set to 1
 * Files: paging.c 
 */

int page_fault_test(){
	TEST_HEADER;

	int i;
	int result = PASS;
	// check first 32 entries of the idt
	for (i = 0; i < 4096; i++){
		uint8_t* x = (uint8_t*)(0x000B8000 + i);
		uint8_t y = *x;
		x = &y;
		// printf("Testing value %x \n",*x);
	}
	for (i = 0; i < 4194304; i++){
		uint8_t* x = (uint8_t*)(0x00400000 + i);
		uint8_t y = *x;
		x = &y;
		// printf("Testing value %x \n",*x);
	} // should not have exception
	return result;
}

/* Page Directory Entry Test
 *
 * Ensures that the zeroth entry in the page directory table (PDT) points to the Page Table (PT) that contains the Page Table PTE to video memory with present and read write bit set && first entry of PDT point to physical address kernel memory
 * Inputs: None
 * Outputs: PASS/FAIL
 * Side Effects: None
 * Coverage: Ensures that entries in PDT and PTE is set correctly
 * Files: paging.c
 */
int page_directory_entry_test()
{
	if(((page_directory[0].val|(((unsigned int)video_mem_page_table)|3))==page_directory[0].val) && \
	((page_directory[1].val|(0x400000|(1<<4)|(1<<7)|(1<<8)|3))==page_directory[1].val))
	{
		return PASS;
	}
	else
	{
		assertion_failure();
		return FAIL;
	}

}

/* Page Table Entry Test
 *
 * Ensures that the 0xB8th entry in the Page Table points to the video memory address and has the present and read write bit set
 * Inputs: None
 * Outputs: PASS/FAIL
 * Side Effects: None
 * Coverage: Ensures that PTE is set correctly
 * Files: paging.c
 */

int page_table_entry_test()
{
	printf("Page table entry : %x \n",video_mem_page_table[0xB8]);
	if(((video_mem_page_table[0xB8].val|(0xB8<<12)|0x3))==video_mem_page_table[0xB8].val)
	{
		return PASS;
	}
	else
	{
		assertion_failure();
		return FAIL;
	}

}

/* Page Fault Test Fail 1
 *
 * Attempts to dereference a memory address that does not have present bit set to 1
 * Inputs: None
 * Outputs: PASS/FAIL
 * Side Effects: None
 * Coverage: If page table set correctly, this access should trigger a page fault
 * Files: paging.c
 */
int page_fault_test_fail1()
{
	uint8_t* x = (uint8_t*) 0x000B7000;
	uint8_t y = *x;
	x = &y;
	return FAIL;
}

/* Page Fault Test Fail 2
 *
 * Attempts to dereference a memory address that does not have present bit set to 1
 * Inputs: None
 * Outputs: PASS/FAIL
 * Side Effects: None
 * Coverage: If page table set correctly, this access should trigger a page fault
 * Files: paging.c
 */


int page_fault_test_fail2()
{
	uint8_t* x = (uint8_t*)0x00400000;
	uint8_t y = *x;
	x = &y;
	return FAIL;
}

/* Divide by zero exception
 *
 * Attempts to divide a value by 0
 * Inputs: None
 * Outputs: PASS/FAIL
 * Side Effects: None
 * Coverage: Should trigger excpetion handler which prints out which excpetion it has invoked
 * Files: isr.c
 */

int divide_by_zero_exception()
{
	int zr= 3-3;
	zr = 5/zr;
	return FAIL;
}

/* Enable Paging Input
 *
 * Attempts to enable paging for NULL pointer(it should point to first entry in page directory table)
 * Inputs: None
 * Outputs: PASS/FAIL
 * Side Effects: None
 * Coverage: it should not allow and return -1
 * Files: paging.c
 */

int enable_paging_input()
{
	int return_value= enable_paging(0x0);
	if(return_value==-1)
	{
		return PASS;
	}
	else
	{
		return FAIL;
	}

}

/* Set Gate Input
 *
 * Attempts to fill up IDT entry using wrong value (i.e. index -1 into IDT, 32bit address of interrupt handler set as 0 ). All these incorrect arguments should cause function to not execute and return -1
 * Inputs: None
 * Outputs: PASS/FAIL
 * Side Effects: None
 * Coverage: set gate input  should only allow correct arguments
 * Files: paging.c
 */


int set_gate_input()
{
	int return_value= set_gate(-1, (uint32_t)isr0, KERNEL_CS) | set_gate(0, 0x0 , KERNEL_CS) | set_gate(-1, (uint32_t)isr0, 0);
	if(return_value==-1)
	{
		return PASS;
	}
	else
	{
		return FAIL;
	}

}
/* Excpetion Handler Input
 *
 * Ensures that function does not exceute if exception number is more than 32
 * Inputs: None
 * Outputs: PASS/FAIL
 * Side Effects: None
 * Coverage: ensures excpetion handler is only invoked if the exception number is less than 32
 * Files: paging.c
 */

int exception_handler_input()
{
	int return_value= exception_handler(32);
	if(return_value==-1)
	{
		return PASS;
	}
	else
	{
		return FAIL;
	}

}

/* PIC_mask_input
 *
 * Ensures enable_irq, disable_irq and send_eoi does not execute if wrong argument passed in
 * Inputs: None
 * Outputs: PASS/FAIL
 * Side Effects: None
 * Coverage: ensures enable-irq disable_irq and send_eoi only works when argumentn is between 0 to 15
 * Files: i8259.c
 */

int pic_mask_input()
{
	int return_value= enable_irq(-1) | disable_irq(-1) | send_eoi(-1) |enable_irq(16) | disable_irq(16) | send_eoi(16);
	if(return_value==-1)
	{
		return PASS;
	}
	else
	{
		return FAIL;
	}

}
#endif
/* Checkpoint 2 tests */
#ifdef CP2_TESTS

/* filesystem_print_files
 *
 * Ensures read_dentry_by_index is working correctly by printing out the first 16 entries' name type and size sequentially
 * Inputs: None
 * Outputs: PASS/FAIL
 * Side Effects: None
 * Coverage: ensures read_dentry_by_index works
 * Files: filesystem.c
 */
int filesystem_print_files(){
	int i = 0;
	// uint8_t* filename = "grep";
	uint8_t fname[32];
	dentry_t dentry;
	dentry.fname = fname;
	for(i = 0; i <17; i++)
	{
		read_dentry_by_index(i, &dentry);
		term_driver(1,(uint8_t*)"File name: ",strlen("File name: "));
		term_driver(1,dentry.fname,32);
		term_driver(1,(uint8_t*)", ",strlen(", "));

		term_driver(1,(uint8_t*)"File type: ",strlen("File type: "));
		term_driver_int(1,dentry.ftype);
		term_driver(1,(uint8_t*)", ",strlen(", "));

		term_driver(1,(uint8_t*)"File size: ",strlen("File size: "));
		term_driver_int(1,get_size(dentry.inode));
		// term_driver(1,"File size: ",strlen("File size: "));

		term_driver(1,(uint8_t*)"\n",1);
	}
	return PASS;
}

/* filesystem_print_file_data
 *
 * Ensures read_data is working. Pass inode number in as argument and populate buffer. Use term_driver to output buff
 * to screen. If contents printed correctly, read_data is correct
 * Inputs: None
 * Outputs: PASS/FAIL
 * Side Effects: None
 * Coverage: ensures read_data works
 * Files: filesystem.c
 */

int filesystem_print_file_data(){
	uint8_t buff[128];
	buff[127] = '\0';
	read_data(53, 0, buff, 127);
	term_driver(1,(uint8_t*)"small file: ",(int32_t)strlen("small file: "));
	term_driver(1,(uint8_t*)buff, (int32_t)strlen((int8_t*)buff));
	term_driver(1,(uint8_t*)"\n",1);

	read_data(44, 0, buff, 127);
	term_driver(1,(uint8_t*)"large file: ",(int32_t)strlen("large file: "));
	term_driver(1,(uint8_t*)buff,(int32_t)strlen((int8_t*)buff));
	term_driver(1,(uint8_t*)"\n",1);

	read_data(5, 0, buff, 127);
	term_driver(1,(uint8_t*)"executable file: ",(int32_t)strlen("executable file: "));
	term_driver(1,(uint8_t*)buff, (int32_t)strlen((int8_t*)buff));
	term_driver(1,(uint8_t*)"\n",1);
	return PASS;
}

/* filesystem_print_fish
 *
 * Ensures read_dentry_by_name is working. Pass frame0.txt as argument and populate dentry with content of frame0.txt
 * Inputs: None
 * Outputs: PASS/FAIL
 * Side Effects: None
 * Coverage: ensures read_dentry_by_name works
 * Files: filesystem.c
 */

int filesystem_print_fish(){
	dentry_t dentry;
	read_dentry_by_name((uint8_t*)"frame0.txt",&dentry);
	uint32_t sz = get_size(dentry.inode);
	uint8_t buff[500];
	read_data(dentry.inode,0,buff,sz);
	buff[sz] = '\0';
	// printf("%s \n",buff);
	term_driver(1,(uint8_t*)buff,128);
	term_driver(1,(uint8_t*)"\n",1);
	return PASS;
}

/* term_spam_test
 *
 * Ensures that term_write only writes the number of bytes passed in nbytes
 * Inputs: None
 * Outputs: Nil
 * Side Effects: None
 * Coverage: ensures term_write only wrties the number of bytes passed in nbytes
 * Files: terminal.c
 */

void term_spam_test(){
	// spam the write ioctl
	int i;
	clear();
	screen_y = 0;
	screen_x = 0;
	for (i = 0; i < 5000; i++){
		term_driver(1, (uint8_t*)"Thi$ is @ test message smaller than 128 characters\n", 51);
	}
	clear();
	for (i = 0; i < 5000; i++){
		term_driver(1, (uint8_t*)"This is a test message smaller than 128 characters 0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000", 128);
	}
	clear();
	screen_x = 0;
	screen_y = 0;
	term_driver(1, (uint8_t*)"The message should stop printing right here 00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000\
	0000", 43);
}

/* term_test
 *
 * Ensures the term_read reads in the characters being typed in the terminal and nothing more than that.
 * Ensures that term_read only reads in nbytes worth of bytes. Anything more than nbytes typed in by user should not be stored in buff
 * Inputs: None
 * Outputs: Nil
 * Side Effects: None
 * Coverage: ensures term_read only read in nbytes worth of bytes into terminal
 * Files: terminal.c
 */

int term_test(){
	// check for buffer overflow
	int i;
	uint8_t buff[128];
	int32_t cnt;

	for (i = 0; i < 128; i++){
		buff[i] = 1; // populate buffer with 1 to check if we are reading too many characters
	}
	term_driver(1, (uint8_t*)"\nPlease type the word 'test' ", 29);
	cnt = term_driver(0, buff, 128);
	if (buff[0] != 't' || buff[1] != 'e' || buff[2] != 's' || buff[3] != 't'){
		return FAIL;
	}
	buff[cnt] = '\0';
	for (i = cnt + 1; i < 128; i++){
		if (buff[i] != 1){
			return FAIL;
		}
	}
	for (i = 0; i < 128; i++){
		buff[i] = 1; // populate buffer with 1 to check if we are reading too many characters
	}
	term_driver(1, (uint8_t*)"\n", 1);
	term_driver(1, (uint8_t*)"Testing read with nbytes of 2, please type 'test' ", 50);
	cnt = term_driver(0, buff, 2);
	buff[cnt] = '\0';

	for (i = cnt + 1; i < 128; i++){
		if (buff[i] != 1){
			return FAIL;
		}
	}
	if (buff[0] != 't' || buff[1] != 'e'){
		return FAIL;
	}

	for (i = 0; i < 128; i++){
		buff[i] = 1; // populate buffer with 1 to check if we are reading too many characters
	}

	term_driver (1, (uint8_t*)"Hi, what's your name? ", 22);
	if (-1 == (cnt = term_driver (0, buff, 128-1))) {
		term_driver (1, (uint8_t*)"Can't read name from keyboard.\n", 30);
	}
	buff[cnt] = '\0';
	term_driver (1, (uint8_t*)"Hello, ", 7);
	term_driver (1, (uint8_t*)buff, cnt);
	term_driver (1, (uint8_t*)"\n", 1);
	return PASS;
}

/* test_term_err_value
 *
 * Passes in invalid argument for term_driver, function should not execute and should return -1
 * Inputs: None
 * Outputs: Nil
 * Side Effects: None
 * Coverage: ensures term_driver does not run if invalid argument passed in
 * Files: terminal.c
 */

int test_term_err_value(){
	uint8_t buff[128];
	int i;
	if (term_driver(0, buff, 129) != -1 ||
		term_driver(1, buff, -43) != -1 ||
		term_driver(3, buff, 60) != 0|| 
		term_driver(1, NULL, 90) != -1|| 
		term_driver(0, NULL, 130) != -1){
			return FAIL;
	}
	for (i = 0; i < 128; i++){
		buff[i] = 1; // populate buffer with 1 to check if we are reading too many characters
	}
	for (i = 0; i < 128; i++){
		if (buff[i] != 1){
			return FAIL;
		}
	}
	// buff should still be untouched
	return PASS;
}

/* test_rtc_frequency
 *
 * Every loop doubles the frequency and increase the ouput char from 1 to 2 to ... to 6
 * Inputs: None
 * Outputs: Nil
 * Side Effects: None
 * Coverage: ensures rtc writes changes frequency correctly
 * Files: rtc.c
 */

void test_rtc_freq(){
	enable_irq(8);
	uint32_t frequency = 2;
	int i;
	int a;
	for (i = 0; i < 6; i++){
		for(a = 0; a < 429999999; a++){;} // stalling function to receive interrupt
		rtc(1, (uint8_t*)&frequency,4);
		test_rtc_c++;
		frequency = frequency * 2;
	}
	uint32_t freq = 2;
	rtc(1,(uint8_t*)&freq,4);
	disable_irq(8);
}

/* test_rtc_err_value
 *
 * Ensures rtc write does not execute if wrong argument passed in (i.e. nbyytes != 4, frequency != power of 2)
 * Inputs: None
 * Outputs: PASS/FAIL
 * Side Effects: None
 * Coverage: ensures rtc writes only execute if the arguments passed in are correct
 * Files: rtc.c
 */

int test_rtc_err_value(){
	uint8_t buff[128];
	uint8_t wrong_freq = 3;
	uint8_t correct_frequency = 4;
	if (rtc(1, buff, 121) != -1 ||
		rtc(-1, buff, 20) != -1 || /*check for invalid cmd*/
		rtc(1,&wrong_freq,4) != -1|| /*check for non power 2 frequency*/
		rtc(1,&correct_frequency,3) != -1|| /*check for invalid nbyte size (3 instead of 4)*/
		rtc(1, NULL, 4) != -1){ /*check for NULL pointer passed in for write*/
			return FAIL;
	}
	return PASS;
}

/* test_rtc_read_open_close_return_value
 *
 * Ensures rtc_open rtc_close rtc_read returns 0
 * Inputs: None
 * Outputs: PASS/FAIL
 * Side Effects: None
 * Coverage: ensures correct return value for rtc read open and close
 * Files: rtc.c
 */

int test_rtc_read_open_close_return_value(){
	uint8_t buff[128];
	if (rtc(2, buff, 4) != 0 || /*calls rtc open, check for return value of 0*/
		rtc(3, buff, 4) != 0  /*calls rtc close, check for return value of 0*/
		|| rtc(0, buff, 2) != 0){ 
			return FAIL;
	}
	return PASS;	
}
#endif
/* Checkpoint 3 tests */
/* Checkpoint 4 tests */
/* Checkpoint 5 tests */


/* Test suite entry point */
void launch_tests(){
	clear();

	/* Checkpoint 1 tests*/
	#ifdef CP1_TESTS
	TEST_OUTPUT("idt_test", idt_test());
	TEST_OUTPUT("idt_entry_test", idt_entry_test());
	TEST_OUTPUT("page_fault_test", page_fault_test());
	TEST_OUTPUT("page_directory_entry_test", page_directory_entry_test());
	TEST_OUTPUT("page_table_entry_test", page_table_entry_test());
	TEST_OUTPUT("enable_paging_input",enable_paging_input());
	TEST_OUTPUT("set_gate_input",set_gate_input());
	TEST_OUTPUT("exception_handler_input",exception_handler_input());
	TEST_OUTPUT("pic_mask_input",pic_mask_input());
	#endif

	/* Checkpoint 2 tests*/
	#ifdef CP2_TESTS
	term_spam_test();
	TEST_OUTPUT((uint8_t*)"term_test",(void*)term_test());
	TEST_OUTPUT((uint8_t*)"test_term_err_value",(void*)test_term_err_value());

	TEST_OUTPUT((uint8_t*)"filesystem_print_files", (void*)filesystem_print_files()); // rtc driver tests
	uint8_t buf[1];
	term_driver(1, (uint8_t*)"Press enter to continue testing...", strlen("Press enter to continue testing..."));
	term_driver(0, buf, 1);
	TEST_OUTPUT((uint8_t*)"filesystem_print_file_data",(void*)filesystem_print_file_data());
	term_driver(1, (uint8_t*)"Press enter to continue testing...", strlen("Press enter to continue testing..."));
	term_driver(0, buf, 1);
	TEST_OUTPUT((uint8_t*)"filesystem_print_fish",(void*)filesystem_print_fish());
	TEST_OUTPUT((uint8_t*)"test_rtc_err_value",(void*)test_rtc_err_value());
	TEST_OUTPUT((uint8_t*)"test_rtc_read_open_close_return_value", (void*)test_rtc_read_open_close_return_value());
	term_driver(1, (uint8_t*)"Press enter to test the RTC...", strlen("Press enter to test the RTC..."));
	term_driver(0, buf, 1);
	test_rtc_freq();
	#endif

}

// void launch_fail_tests(int arg)
// {
// 	clear();
// 	switch(arg)
// 	{
// 		case 0:
// 			TEST_OUTPUT("page_fault_test_fail1",page_fault_test_fail1());
// 			break;
// 		case 1:
// 			TEST_OUTPUT("page_fault_test_fail2",page_fault_test_fail2());
// 			break;
// 		case 2:
// 			TEST_OUTPUT("divide_by_zero_exception",divide_by_zero_exception());
// 			break;

// 		default:
// 		break;
// 	}
// }
