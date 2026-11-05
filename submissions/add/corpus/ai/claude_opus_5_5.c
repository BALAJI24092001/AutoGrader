/* Source: Claude Opus 5.5 (Anthropic).
   Prompt: "Write a clean C program that reads two integers and prints their
   sum without overflow. Use a helper function." */
#include <stdio.h>

/* Add two ints in a wider type so the sum cannot overflow. */
long long add(int x, int y)
{
    return (long long)x + y;
}

int main(void)
{
    int x, y;
    if (scanf("%d %d", &x, &y) != 2) {
        fprintf(stderr, "expected two integers\n");
        return 1;
    }
    printf("%lld\n", add(x, y));
    return 0;
}
