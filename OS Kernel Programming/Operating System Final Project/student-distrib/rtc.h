#ifndef _RTC_H
#define _RTC_H

void rtc_init(void);
void set_rtc_rate(uint32_t rate);

int32_t rtc_read();
int32_t rtc_write(const void* buf);
int32_t rtc_open();
int32_t rtc_close();

volatile extern int rtc_flag;

#endif /* _I8259_H */
