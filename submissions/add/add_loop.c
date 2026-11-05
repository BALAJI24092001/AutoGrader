#include <stdio.h>

/* Adds b to a one step at a time, so the time grows with the size of b. */
int add(int a, int b)
{
    while (b > 0) {
        a++;
        b--;
    }
    while (b < 0) {
        a--;
        b++;
    }
    return a;
}

int main(void)
{
    int a, b;
    if (scanf("%d %d", &a, &b) != 2) {
        return 1;
    }
    printf("%d\n", add(a, b));
    return 0;
}
