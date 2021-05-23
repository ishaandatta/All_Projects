# Juice: [(key, value)] --> [(key, value)]
import sys
from typing import Tuple

def main():
  groups = {}
  for line in sys.stdin:
    key, Ca, k = line.strip().split('\t')
    key = int(key)
    score = (Ca, int(k))
    if key not in groups:
      groups[key] = []
    groups[key].append(score)
  for key, value in groups.items():
    juice(key, value)

def juice(key: int, value: [Tuple[str, int]]):
  scores = {}
  for Ca, k in value:
    if Ca not in scores:
      scores[Ca] = 0
    scores[Ca] += k
  most_doms = 0
  most_dom_candidates = []
  m = len(scores)
  for Ca, num_doms in scores.items():
    if num_doms > most_doms:
      most_dom_candidates = [Ca]
      most_doms = num_doms
    elif num_doms == most_doms:
      most_dom_candidates.append(Ca)
  print('\t'.join(most_dom_candidates))

if __name__ == '__main__':
  if len(sys.argv) != 1:
    exit(1)
  main()