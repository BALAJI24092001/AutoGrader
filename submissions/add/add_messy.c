#include <stdio.h>

/* Gives the right answers, but everything is crammed into one long main()
   full of branches, and one variable is never used (a compiler warning). */
int main(void)
{
    long long a, b, sum;
    int unused;
    int ok = scanf("%lld %lld", &a, &b);
    if (ok == EOF) {
        return 1;
    }
    if (ok != 2) {
        return 1;
    }
    if (a == 0) {
        sum = b;
    } else if (b == 0) {
        sum = a;
    } else if (a > 0 && b > 0) {
        sum = a + b;
    } else if (a < 0 && b < 0) {
        sum = a + b;
    } else if (a > 0 && b < 0) {
        sum = a;
        sum = sum + b;
    } else {
        sum = b;
        sum = sum + a;
    }
    if (sum == 0) {
        printf("0\n");
        return 0;
    }
    if (sum > 0) {
        printf("%lld\n", sum);
        return 0;
    }
    if (sum < 0) {
        printf("%lld\n", sum);
        return 0;
    }
    printf("%lld\n", sum);
    return 0;
}
