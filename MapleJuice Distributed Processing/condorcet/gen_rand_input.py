# Juice: [(key, value)] --> [(key, value)]
import random
import sys
import math

random.seed(0)

def main():
  d = math.ceil(math.log(M, 16))
  candidates = ['{0:0{1}x}'.format(i,d) for i in range(M)]
  for x in range(N):
    random.shuffle(candidates)
    print('\t'.join(candidates))

if __name__ == '__main__':
  global N, M
  N = 100000
  M = 3
  if (len(sys.argv) > 1):
    N = int(sys.argv[1])
  if (len(sys.argv) > 2):
    M = int(sys.argv[2])
  main()