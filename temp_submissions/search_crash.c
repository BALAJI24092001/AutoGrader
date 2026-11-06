#include <stdio.h>
#include <stdlib.h>

/* Look at position i, then search the rest of the array. */
int search(int *arr, int i, int n, int target)
{
    if (arr[i] == target)
        return i;
    if (i == n - 1)
        return -1;
    return search(arr, i + 1, n, target);
}

int main(void)
{
    int n, target;
    scanf("%d", &n);
    int *arr = malloc(n * sizeof(int));
    for (int i = 0; i < n; i++)
        scanf("%d", &arr[i]);
    scanf("%d", &target);
    printf("%d\n", search(arr, 0, n, target));
    free(arr);
    return 0;
}
