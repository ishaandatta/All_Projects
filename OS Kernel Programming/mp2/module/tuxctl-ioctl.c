/* tuxctl-ioctl.c
 *
 * Driver (skeleton) for the mp2 tuxcontrollers for ECE391 at UIUC.
 *
 * Mark Murphy 2006
 * Andrew Ofisher 2007
 * Steve Lumetta 12-13 Sep 2009
 * Puskar Naha 2013
 */

#include <asm/current.h>
#include <asm/uaccess.h>

#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/module.h>
#include <linux/fs.h>
#include <linux/sched.h>
#include <linux/file.h>
#include <linux/miscdevice.h>
#include <linux/kdev_t.h>
#include <linux/tty.h>
#include <linux/spinlock.h>

#include "tuxctl-ld.h"
#include "tuxctl-ioctl.h"
#include "mtcp.h"

#define debug(str, ...) \
	printk(KERN_DEBUG "%s: " str, __FUNCTION__, ## __VA_ARGS__)


#define low_16_bits 0xFFFF
#define low_4_bits 0x0F
#define LED_arg_size 6

/* Locks to protect global variables */
static spinlock_t led_lock = SPIN_LOCK_UNLOCKED;
static spinlock_t buttons_lock = SPIN_LOCK_UNLOCKED;
static spinlock_t flag_bioc_lock = SPIN_LOCK_UNLOCKED;
static spinlock_t flag_led_lock = SPIN_LOCK_UNLOCKED;
/* Global variables */
static volatile char led_status[LED_arg_size]; //Saves last argument passed to set LED display (last state of LEDs)
static volatile unsigned size;		//Saves size of last argument passed to set LED
static volatile unsigned buttons_status = 0xFF; //Saves currently pressed buttons (active low)
static volatile uint8_t flag_bioc;	//Flag for BIOC, set to high during each call to set BIOC on (active high)
static volatile uint8_t flag_led; 	//Flag LED, set to high during each put call to LED display (active high)

/* Local functions- see function headers for more details */
int tux_init (struct tty_struct* tty);
int clear_state (struct tty_struct* tty);
int tux_buttons (struct tty_struct* tty, unsigned long arg);
int set_led (struct tty_struct* tty, unsigned long arg);
int ack_handle (struct tty_struct* tty);

/* Table to get the value to display on LED for each corresponding character.
	Values are - 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, A, B, C, D, E, F   */
unsigned char LED_bytes[16] = {
0xE7, 0x6, 0xCB, 0x8F, 0x2E, 0xAD, 0xED, 0x86, 0xEF, 0xAF, 0xEE, 0xEF,
0xE1, 0xE7, 0xE9, 0xE8
};
/************************ Protocol Implementation *************************/

/* tuxctl_handle_packet()
 * IMPORTANT : Read the header for tuxctl_ldisc_data_callback() in 
 * tuxctl-ld.c. It calls this function, so all warnings there apply 
 * here as well.
 * DESCRIPTION: Handles receiving commands for Reset, Ack and BIOC events.
 *   INPUTS: tty -- struct to communicate with the Tux
 * 				packet -- character array with relevant data
 *   OUTPUTS: none
 *   RETURN VALUE: none
 *   SIDE EFFECTS: Handles the different cases, depending on the passed packet.
 */
void tuxctl_handle_packet (struct tty_struct* tty, unsigned char* packet)
{
    unsigned a, b, c;
	unsigned long flags = 0;
	unsigned char temp1, temp2;
	uint8_t bioc;
	uint8_t led;
	char argument[LED_arg_size];
	unsigned size_ = 0;
	unsigned i = 0;

    a = packet[0]; /* Avoid printk() sign extending the 8-bit */
    b = packet[1]; /* values when printing them. */
    c = packet[2];

	switch(a){
		case MTCP_RESET:
			//Clear BIOC flag
			spin_lock_irqsave(&flag_bioc_lock, flags);
			flag_bioc = 0;
			spin_unlock_irqrestore(&flag_bioc_lock, flags);
			//Clear LED flag
			spin_lock_irqsave(&flag_led_lock, flags);
			flag_led = 0;
			spin_unlock_irqrestore(&flag_led_lock, flags);
			tux_init(tty);
			return;
		case MTCP_ACK:  			/* MTCP_ACK: Handles restoring LED state for Reset and clearing the LED flag*/
			spin_lock_irqsave(&flag_bioc_lock, flags);
			bioc = flag_bioc;
			spin_unlock_irqrestore(&flag_bioc_lock, flags);
			spin_lock_irqsave(&flag_led_lock, flags);
			led = flag_led;
			spin_unlock_irqrestore(&flag_led_lock, flags);

		/*if BIOC flag high and LED clear => clear BIOC, 
			restore LED state and set LED flag to high*/
			if(bioc){		
				//Clear bioc flag
				spin_lock_irqsave(&flag_bioc_lock, flags);
				flag_bioc = 0;
				spin_unlock_irqrestore(&flag_bioc_lock, flags);
				//Restore state of LED
				spin_lock_irqsave(&led_lock, flags);
				for(i = 0; i < size; i++){
					argument[i] = led_status[i];
				}
				size_ = size;
				spin_unlock_irqrestore(&led_lock, flags);
				//Set LED flag to high and restore/initialise LED state
				spin_lock_irqsave(&flag_led_lock, flags);
				flag_led = 1;
				spin_unlock_irqrestore(&flag_led_lock, flags);

				tuxctl_ldisc_put(tty, argument, size_);
			}
			else if(led && (!bioc)){		//if LED flag high and BIOC low, clear LED flag
				//if LED flag high and BIOC low, clear LED flag
				spin_lock_irqsave(&flag_led_lock, flags);
				flag_led = 0;
				spin_unlock_irqrestore(&flag_led_lock, flags);
			}
			return;
		
		case MTCP_BIOC_EVENT:
			temp1 = (c & 4) << 3; // And with 4 to get down bit, shift to place it in the 6th bit
			temp2 = (c & 2) << 5; //And with 2 to get left bit, shift it to 7th bit
			b = b & 0x0F;		//get low 4 bits
			c = (c & 9) << 4;		//and with binary 1001 (get right and up bits, leave out down and left)
			temp1 = b | c | temp1 | temp2;		//create the correct sequence of bytes 
			spin_unlock_irqrestore(&buttons_lock, flags);
			buttons_status = temp1;
			spin_unlock_irqrestore(&buttons_lock, flags);

			return;

		default: 
			return;
	}
    /*printk("packet : %x %x %x\n", a, b, c); */
}

/******** IMPORTANT NOTE: READ THIS BEFORE IMPLEMENTING THE IOCTLS ************
 *                                                                            *
 * The ioctls should not spend any time waiting for responses to the commands *
 * they send to the controller. The data is sent over the serial line at      *
 * 9600 BAUD. At this rate, a byte takes approximately 1 millisecond to       *
 * transmit; this means that there will be about 9 milliseconds between       *
 * the time you request that the low-level serial driver send the             *
 * 6-byte SET_LEDS packet and the time the 3-byte ACK packet finishes         *
 * arriving. This is far too long a time for a system call to take. The       *
 * ioctls should return immediately with success if their parameters are      *
 * valid.                                                                     *
 *                                                                            *
 ******************************************************************************/
/* tuxctl_ioctl()
 * DESCRIPTION: IOCTL for Initializing, Buttons and Set LED commands.
 *   INPUTS: tty -- struct to communicate with the Tux
 * 				file -- file pointer for tux
 * 				cmd -- issued command
 * 				arg -- passed argument relevant to the command
 *   OUTPUTS: none
 *   RETURN VALUE: none
 *   SIDE EFFECTS: Handles the different cases, depending on the command.
 */
int 
tuxctl_ioctl (struct tty_struct* tty, struct file* file, 
	      unsigned cmd, unsigned long arg)
{
    switch (cmd) {
	case TUX_INIT:
		clear_state(tty);
		tux_init(tty);
		return 0;
	case TUX_BUTTONS:
		tux_buttons(tty, arg);
		return 0;
	case TUX_SET_LED:
		set_led(tty, arg);
		return 0;
	case TUX_LED_ACK:
	case TUX_LED_REQUEST:
	case TUX_READ_LED:
	default:
	    return -EINVAL;
    }
}

/* 
 * tux_init
 *   DESCRIPTION: Initializes the Tux. Helper function which sets
 * 		LEDs to user mode and enables button-interrupt on change.
 *   INPUTS: tty -- struct to communicate with the Tux
 *   OUTPUTS: none (returns 0)
 *   RETURN VALUE: none
 *   SIDE EFFECTS: Sets LED User mode and Button-interrupt on change.
 */

int tux_init (struct tty_struct* tty){
	unsigned long flags;
	char cmd = MTCP_LED_USR;

	spin_lock_irqsave(&flag_bioc_lock, flags);
	flag_bioc = 1;	
	spin_unlock_irqrestore(&flag_bioc_lock, flags);

	tuxctl_ldisc_put(tty, &cmd, 1);
	cmd = MTCP_BIOC_ON;
	tuxctl_ldisc_put(tty, &cmd, 1);

	return 0;
}

/* 
 * clear_state
 *   DESCRIPTION: Helper function which helps initializing the Tux.
 * 		Initializes global variables/flags.
 *   INPUTS: tty -- struct to communicate with the Tux
 *   OUTPUTS: none
 *   RETURN VALUE: none
 *   SIDE EFFECTS: Initializes global variables/flags.
 */
int clear_state (struct tty_struct* tty){
	unsigned long flags;
	unsigned i;
	char t[LED_arg_size] = { MTCP_LED_SET, 0x7, 0xEE, 0xEF, 0xE1 };

	//Set led_status
	spin_lock_irqsave(&led_lock, flags);
	for(i = 0; i < 6; i++){
		led_status[i] = t[i];
	}
	size = LED_arg_size;
	spin_unlock_irqrestore(&led_lock, flags);
	//Clear BIOC flag
	spin_lock_irqsave(&flag_bioc_lock, flags);
	flag_bioc = 0;
	spin_unlock_irqrestore(&flag_bioc_lock, flags);
	//Clear LED flag
	spin_lock_irqsave(&flag_led_lock, flags);
	flag_led = 0;
	spin_unlock_irqrestore(&flag_led_lock, flags);
	return 0;
}

/* 
 * tux_buttons
 *   DESCRIPTION: Receives pointer to 32 bit integer. Sets its low 8 bits
 * 					to current button state. (currently pressed buttons)
 *   INPUTS:  tty -- struct to communicate with the Tux
 * 				arg -- pointer to 32 bit integer whose low byte is to be set
 *   OUTPUTS: none (returns 0)
 *   RETURN VALUE: none
 *   SIDE EFFECTS: Sets lowest byte of passed arg to current button state
 */

int tux_buttons (struct tty_struct* tty, unsigned long arg){
		unsigned long flags;	
		unsigned long arg_;

		if(!arg) return -EINVAL;
		else{
			spin_lock_irqsave(&buttons_lock, flags);
			arg_ = buttons_status;	//Save to global variable
			spin_unlock_irqrestore(&buttons_lock, flags);
			copy_to_user((unsigned long*)arg, &arg_, 1);

		}
		return 0;
}

/* 
 * set_led
 *   DESCRIPTION: Receives 32 bit integer with the required values to send to the LED.
				The function parses the received argument, creates a character array of 
				the argument to be sent in the SET_LED call and saves it in the global
				variable led_status, then checks the LED ack before calling set LED 
				and setting the flag to high.
 *   INPUTS: tty_struct tty -- struct to communicate with the Tux 
 * 				arg -- 32 bit integer of the form: low 16-bits specify a number whose
				hexadecimal value is to be displayed. The low 4 bits of the third byte
				specifies which LED’s should be turned on. The low 4 bits of the highest byte
				specify whether the corresponding decimal points should be turned on.
 *   OUTPUTS: none
 *   RETURN VALUE: none (returns 0)
 *   SIDE EFFECTS: Saves new LED state to global variable, sets LED flag if its not 
 * 					already high and issues SET_LED, otherwise drops the packet.
 */
int set_led (struct tty_struct* tty, unsigned long arg){

	unsigned long flags;
	char argument[LED_arg_size]; 	//Set to max possible size of argument to be passed to SET_LED
	char temp = 0;
	char ledsToSet;
	unsigned display_val;
	unsigned j, i;

	argument[0] = (char) MTCP_LED_SET; //set first byte in array to Opcode

	ledsToSet = (arg & 0x0F0000) >> 16; //get low 4 bits of third byte
	argument[1] = ledsToSet;				//set 2nd byte in array to specify LED's to set 
	
	display_val = arg & low_16_bits; // get low 16 bits (hex value to be printed)
	temp = (arg & 0xF000000) >> 24; // get low 4 bits of highest byte (decimal point values for LEDs)
	j = 2;

	for(i = 0; i < 4; i++){		//Iterate over the low 16 bits
		if(ledsToSet & 1){
			int val = display_val & low_4_bits;
			unsigned char a = LED_bytes[val];  //get argument for digit on display
			if(temp & 1){			//if decimanl point enabled, set it in the byte
				a = a + 16;
			}
			argument[j] = a;
			j++;
		}
		temp = temp >> 1;		//shift out lowest bit
		display_val = display_val >> 4;	//shift out lowest 4 bits
		ledsToSet = ledsToSet >> 1;	//shift out lowest bit
	}
	//Save argument and size in global variables
	spin_lock_irqsave(&led_lock, flags);
	for(i = 0; i < j; i++){
		led_status[i] = argument[i];
	}
	size = j;
	spin_unlock_irqrestore(&led_lock, flags);
	/* if led flag high(in use), drop request. Else set led_flag & call put to LEDs */
	spin_lock_irqsave(&flag_led_lock, flags);
	if(flag_led){
		spin_unlock_irqrestore(&flag_led_lock, flags);
		return 0;
	}
	else{
		flag_led = 1;
		spin_unlock_irqrestore(&flag_led_lock, flags);
		tuxctl_ldisc_put(tty, &argument[0], j);
	}
	return 0;
}

