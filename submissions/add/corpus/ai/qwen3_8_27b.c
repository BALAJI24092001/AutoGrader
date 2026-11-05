/* Source: Groq, model qwen/qwen3.8-27b, temperature 0, seed 42.
   Prompt: "Write a C program that reads two integers from standard input
   and prints their sum. Reply with only the code." */
#include <stdio.h>

int main() {
    int a, b;
    scanf("%d %d", &a, &b);
    printf("%d\n", a + b);
    return 0;
}
