import sys
import os

lines = sys.stdin.readlines()

for line in lines:
    for word in line.rstrip('\n').split():
        for word in line.split():
            print(f"{word} 1")