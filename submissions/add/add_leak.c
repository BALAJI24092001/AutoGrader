#include <stdio.h>
#include <stdlib.h>

/* Gives the right answers, but the memory from malloc is never freed,
   so the program leaks it (LeakSanitizer reports this). */
int main(void)
{
    long long *numbers = malloc(2 * sizeof(long long));
    if (numbers == NULL) {
        return 1;
    }
    if (scanf("%lld %lld", &numbers[0], &numbers[1]) != 2) {
        return 1;
    }
    printf("%lld\n", numbers[0] + numbers[1]);
    return 0;
}
