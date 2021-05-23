import random

dictionary = [x.strip().upper() for x in open('/usr/share/dict/words')]

with open('local/dict.txt', "w+") as f:
    total_bytes = 0
    while total_bytes < (1000*1000*100):
        for i in range(0, 26):
            letter = chr(ord('A')+i)
            starts_with = ', '.join([word for word in dictionary if word.startswith(letter)])
            
            f.write(starts_with)
            total_bytes += len(starts_with)