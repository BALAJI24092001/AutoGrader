/* Source: https://www.geeksforgeeks.org/c-program-to-add-two-integers/
   ("1. Using the + Operator"), copied 2026-10-24. */
#include <stdio.h>

int main() {
    int a, b, sum = 0;

    // Read two numbers from the user
    printf("Enter two integers: ");
    scanf("%d %d", &a, &b);

    // Calculate the addition of a and b
    // using '+' operator
    sum = a + b;

    printf("Sum: %d", sum);

    return 0;
}
