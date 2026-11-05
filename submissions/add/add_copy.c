#include <stdio.h>

/* A copy of add_good.c with every name and comment changed, to show that
   the originality check still finds it. */
long long plus(long long x_value, long long y_value)
{
    return x_value + y_value;
}

int main(void)
{
    long long x_value, y_value;

    if (scanf("%lld %lld", &x_value, &y_value) != 2) {
        return 1;   /* bad input */
    }
    printf("%lld\n", plus(x_value, y_value));
    return 0;
}
