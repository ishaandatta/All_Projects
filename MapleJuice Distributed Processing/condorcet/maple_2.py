# Maple <input_file> --> [(key, value)]
import sys
from typing import List

def main(input_file):
  with open(input_file, 'r') as f:
    [print('1\t' + line.strip()) for line in f.readlines()]

if __name__ == '__main__':
  if len(sys.argv) != 2:
    exit(1)
  input_file = sys.argv[1]
  main(input_file)