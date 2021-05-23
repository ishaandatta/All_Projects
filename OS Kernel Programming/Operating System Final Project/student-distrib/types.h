/* types.h - Defines to use the familiar explicitly-sized types in this
 * OS (uint32_t, int8_t, etc.).  This is necessary because we don't want
 * to include <stdint.h> when building this OS
 * vim:ts=4 noexpandtab
 */

#ifndef _TYPES_H
#define _TYPES_H

#define NULL 0

#ifndef ASM

/* Constants for video memory/VGA text mode */
#define VIDEO       0xB8000
#define NUM_COLS    80
#define NUM_ROWS    25
#define VID_BUF_SIZE    NUM_COLS * NUM_ROWS 
#define ATTRIB      0x7
#define NUM_TERM    3

/* Masks and other useful constants */
#define THREE_BIT_MASK 0x07 // mask to get lowest 8 bits
#define EIGHT_BIT_MASK 0xFF // mask to get lowest 8 bits
#define SIXTEEN_BIT_MASK 0xFFFF
#define EIGHT_TO_FIFTEEN_MASK   0xFF00 // mask to get bits 8 to 15

/* Stack segments */
#define KERNEL_CS   0x0010
#define KERNEL_DS   0x0018
#define USER_CS     0x0023
#define USER_DS     0x002B
#define KERNEL_TSS  0x0030
#define KERNEL_LDT  0x0038
#define USER_VIRTUAL_START_ADDR   0x8000000
#define USER_VIRTUAL_END_ADDR   0x8400000


/* Useful large constants */
#define MB_4    0x400000
#define MB_8    MB_4 * 2
#define KB_8    0x2000  

/* Buffer constants */
#define MAX_BUFF_SIZE   128
#define CHAR_LIMIT MAX_BUFF_SIZE - 1

/* IRQ Numbers */
#define RTC_IRQ 8 // rtc irq number

/* Scheduling Constants */
#define PIT_FREQ    40// frequency of the PIT

/* FD ops table */
#define FILE_OPEN       0
#define FILE_READ       1
#define FILE_WRITE      2
#define FILE_CLOSE      3


/* Types defined here just like in <stdint.h> */
typedef int int32_t;
typedef unsigned int uint32_t;

typedef short int16_t;
typedef unsigned short uint16_t;

typedef char int8_t;
typedef unsigned char uint8_t;

#endif /* ASM */

#endif /* _TYPES_H */
