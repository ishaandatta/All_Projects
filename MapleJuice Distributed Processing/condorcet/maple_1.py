#   python3 maple.py input.txt | python3 juice_1.py > temp.txt; python3 maple_2.py temp.txt | python3 juice_2.py > output.txt
# OR (slower)
#   pip3 install pyinstaller; pyinstaller --onefile maple*.py; pyinstaller --onefile juice*.py; 
#   time ./maple_1 input.txt | ./juice_1 > temp.txt; ./maple_2 temp.txt | ./juice_2 > output.txt

# Maple <input_file> --> [(key, value)]
from typing import List
import sys

K = 100

def main(input_file):
  with open(input_file, 'r') as f:
    batch = None
    while (batch is None or batch[-1] != ['']):
      batch = [next(f, '').strip().split('\t') for i in range(K)]
      maple(None, batch)
  
def maple(key: None, value: List[List[str]]):
  for vote in value:
    if vote == []:
      break
    for i, Vi in enumerate(vote[:-1]): 
      for Vj in vote[i+1:]:
        if Vi < Vj:
          print(f'{Vi}\t{Vj}\t{1}')
        else:
          print(f'{Vj}\t{Vi}\t{-1}')

if __name__ == '__main__':
  if len(sys.argv) != 2:
    exit(1)
  input_file = sys.argv[1]
  main(input_file)