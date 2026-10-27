#include <stdio.h>

/* Adds by counting up one step at a time, but forgets to decrease b,
   so the loop never ends. */
int main(void)
{
    int a, b;
    scanf("%d %d", &a, &b);
    while (b > 0) {
        a++;
    }
    printf("%d\n", a);
    return 0;
}
