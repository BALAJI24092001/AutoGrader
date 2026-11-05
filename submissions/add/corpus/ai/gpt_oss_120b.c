/* Source: Groq, model openai/gpt-oss-120b, temperature 0, seed 42.
   Prompt: "Write a C program that reads two integers from standard input
   and prints their sum. Reply with only the code." */
#include <stdio.h>

int main(void) {
    int a, b;
    if (scanf("%d %d", &a, &b) != 2) {
        return 1; // Input error
    }
    printf("%d\n", a + b);
    return 0;
}
