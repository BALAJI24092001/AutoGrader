#include <stdio.h>

/* Stores the result through a pointer that was never given any memory,
   so the program crashes (segmentation fault). */
int main(void)
{
    int a, b;
    int *result = NULL;
    scanf("%d %d", &a, &b);
    *result = a + b;
    printf("%d\n", *result);
    return 0;
}
