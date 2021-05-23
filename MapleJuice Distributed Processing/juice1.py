import sys
import os

ret = 0

for line in sys.stdin.readlines():
    line = line.rstrip('\n')
    if line:
        ret += int(line)

print(ret)