#include <stdio.h>
#include <stdlib.h>

/* Return the index of the first value equal to target, or -1. */
int find_first(const int *values, int n, int target)
{
    for (int i = 0; i < n; i++) {
        if (values[i] == target) {
            return i;
        }
    }
    return -1;
}

int main(void)
{
    int n, target;

    if (scanf("%d", &n) != 1 || n < 0) {
        return 1;
    }
    /* n + 1 so that malloc never gets 0 when the array is empty */
    int *values = malloc((n + 1) * sizeof *values);
    if (values == NULL) {
        return 1;
    }
    for (int i = 0; i < n; i++) {
        if (scanf("%d", &values[i]) != 1) {
            free(values);
            return 1;
        }
    }
    if (scanf("%d", &target) != 1) {
        free(values);
        return 1;
    }
    printf("%d\n", find_first(values, n, target));
    free(values);
    return 0;
}
