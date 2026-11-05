#include <stdio.h>

/* Return the sum of two integers. long long holds any sum of two ints,
   so INT_MAX + 1 does not overflow. */
long long add(long long first, long long second)
{
    return first + second;
}

int main(void)
{
    long long first, second;

    if (scanf("%lld %lld", &first, &second) != 2) {
        return 1;   /* input was not two integers */
    }
    printf("%lld\n", add(first, second));
    return 0;
}
