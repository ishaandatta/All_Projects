import os
import sys


filename1 = 'maple1.txt'
filename2 = 'maple2.txt'
ret = []

with open(filename1, 'r') as f:
    text = f.readlines()
    lines = [line.lower() for line in text]

for i in range(len(lines)):
    lines[i] = lines[i].rstrip('\n')

    if not lines[i]:
        break

    idx = lines[i].find('.') 
    while idx != -1:
        if idx != len(lines[i])-1:
            lines[i] = lines[i][:idx+1] + '\n' + lines[i][idx+2:]
        idx = lines[i].find('.', idx+1)

    idx = lines[i].find(',') 
    while idx != -1:
        if lines[i][idx+1] != '\n':
            lines[i] = lines[i][:idx+1] + '\n' + lines[i][idx+2:]
        idx = lines[i].find(',', idx+1)

for i in range(len(lines)):
    lines[i] = lines[i].split('\n')

for line in lines:
    if line:
        for sen in line:
            ret.append(f"{sen[:-1]}\n")

with open(filename2, 'w') as out:
    out.writelines(ret)