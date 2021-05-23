#include <stdio.h>
#include <string.h>

#define BATCH_SZE 100
#define MAX_FIELD_LEN 20
#define MAX_FIELDS 1024

int get_next_vote(FILE *fp, char vote[MAX_FIELDS][MAX_FIELD_LEN]) {
    int i = 0;
    int j = 0;
    while(1) {
        char c = fgetc(fp);
        if (c == '\n' || c == EOF || c == '\0') {
            vote[i][j] = '\0';
            i++; j = 0;
            vote[i][j] = '\0';
            return c == EOF ? -i : i;
        } else if (c == '\t') {
            vote[i][j] = '\0';
            i++; j = 0;
        } else {
            vote[i][j++] = c; 
        }
    }
}

int main( int argc, char *argv[] )  {
    FILE *fp = fopen (argv[1], "r");

    char vote[MAX_FIELDS][MAX_FIELD_LEN];
    int m;
    while ((m=get_next_vote(fp, vote)) > 0) {
        m = m < 0 ? m*-1 : m;
        for (int i = 0; i < m - 1; i++) {
            for (int j = i + 1; j < m; j++) {
                if (strcmp(vote[i], vote[j]) < 0) {
                    printf("%s\t%s\t%d\n", vote[i], vote[j], 1);
                } else {
                    printf("%s\t%s\t%d\n", vote[j], vote[i], -1);
                }
            }
        }
    }

    fclose(fp);
}