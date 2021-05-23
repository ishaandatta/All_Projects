#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
#include <math.h>

#define BATCH_SZE 100
#define MAX_FIELD_LEN 20
#define MAX_FIELDS 1024
#define FIELD_DELIM '\t'
#define LINE_DELIM '\n'

void shuffle(char x[MAX_FIELDS][MAX_FIELD_LEN], int M) {
  char temp[MAX_FIELD_LEN];
  for (int i = 0; i < M-1; i++) {
      int j = rand() % (M-i) + i;
      if (i == j) {
        continue;
      }
      strcpy(temp, x[i]);
      strcpy(x[i], x[j]);
      strcpy(x[j], temp);
  }
}

int main( int argc, char *argv[] )  {
  int N = argc > 1 ? atoi(argv[1]) : 100000;
  int M = argc > 2 ? atoi(argv[2]) : 3;
  
  char candidates[MAX_FIELDS][MAX_FIELD_LEN];
  for (int j = 0; j < M; j++) {
    char format[32];
    int digits = ceil((float)log(M) / log(16));
    strcpy(format, "%0");
    sprintf(&(format[2]), "%dx", digits);
    sprintf(candidates[j], format, j);
  }

  srand(0);

  for (int i = 0; i < N; i++) {
    shuffle(candidates, M);
    for (int j = 0; j < M; j++) {
      if (j == M-1) {
        printf("%s\n", candidates[j]);
      } else {
        printf("%s\t", candidates[j]);
      }
    }
  }
}