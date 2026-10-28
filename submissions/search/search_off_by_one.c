#include <stdio.h>

int main()
{
    int n, t;
    scanf("%d", &n);
    int a[n];
    for (int i = 0; i < n; i++)
        scanf("%d", &a[i]);
    scanf("%d", &t);
    int pos = -1;
    for (int i = 0; i < n - 1; i++) {
        if (a[i] == t) {
            pos = i;
            break;
        }
    }
    printf("%d\n", pos);
    return 0;
}
