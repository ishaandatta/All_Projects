#include <stdio.h>
#include <stdlib.h>

#define BATCH_SZE 100
#define MAX_FIELD_LEN 20
#define MAX_FIELDS 1024
#define FIELD_DELIM '\t'
#define LINE_DELIM '\n'

int main( int argc, char *argv[] )  {
    FILE *fp = fopen (argv[1], "r");

    char *line_buf = NULL;
    size_t line_buf_size = 0;
    int line_size;
    while ((line_size = getline(&line_buf, &line_buf_size, fp)) >= 0) {
        printf("1\t%s", line_buf);
    }

    free(line_buf);
    line_buf = NULL;

    fclose(fp);
}