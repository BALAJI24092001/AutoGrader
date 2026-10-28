#include <stdio.h>
#include <stdlib.h>

/* Sort the values (and their positions) with bubble sort. Bubble sort keeps
   equal values in their original order, so the first match stays first. */
void sort_pairs(int *values, int *positions, int n)
{
    for (int i = 0; i < n - 1; i++) {
        for (int j = 0; j < n - 1 - i; j++) {
            if (values[j] > values[j + 1]) {
                int v = values[j];
                values[j] = values[j + 1];
                values[j + 1] = v;
                int p = positions[j];
                positions[j] = positions[j + 1];
                positions[j + 1] = p;
            }
        }
    }
}

/* Binary search for the leftmost copy of target in the sorted values. */
int leftmost(const int *values, int n, int target)
{
    int low = 0, high = n;
    while (low < high) {
        int mid = low + (high - low) / 2;
        if (values[mid] < target)
            low = mid + 1;
        else
            high = mid;
    }
    if (low < n && values[low] == target)
        return low;
    return -1;
}

int main(void)
{
    int n, target;
    if (scanf("%d", &n) != 1 || n < 0)
        return 1;
    int *values = malloc((n + 1) * sizeof(int));
    int *positions = malloc((n + 1) * sizeof(int));
    if (values == NULL || positions == NULL)
        return 1;
    for (int i = 0; i < n; i++) {
        if (scanf("%d", &values[i]) != 1)
            return 1;
        positions[i] = i;
    }
    if (scanf("%d", &target) != 1)
        return 1;

    sort_pairs(values, positions, n);
    int k = leftmost(values, n, target);
    printf("%d\n", k < 0 ? -1 : positions[k]);
    free(values);
    free(positions);
    return 0;
}
