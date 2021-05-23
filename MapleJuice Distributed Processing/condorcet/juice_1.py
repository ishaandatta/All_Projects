# Juice: [(key, value)] --> [(key, value)]
import sys
from typing import List, Tuple

def main():
  groups = {}
  for line in sys.stdin:
    Ca, Cb, val = line.strip().split('\t')
    pair = (Ca, Cb)
    val = int(val)
    if pair not in groups:
      groups[pair] = []
    groups[pair].append(val)
  for key, value in groups.items():
    juice(key, value)

def juice(key: Tuple[str, str], value: List[int]):
  (Ca, Cb) = key
  net_doms = sum(value)
  if net_doms > 0:
    print(f"{Ca}\t{1}")
    print(f"{Cb}\t{0}")
  elif net_doms < 0:
    print(f"{Ca}\t{0}")
    print(f"{Cb}\t{1}")
  else:
    print(f"{Ca}\t{0}")
    print(f"{Cb}\t{0}")

if __name__ == '__main__':
  if len(sys.argv) != 1:
    exit(1)
  main()