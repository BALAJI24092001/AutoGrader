# Tests for linear_search

Input: the first line is n, the second line has n integers, the third line is
the target. The program prints the 0-based index of the first number equal to
the target, or -1 if there is none.

Each test is a pair of files: `NN.in` is fed to the program on standard input,
and `NN.out` is the output we expect.

| Test | Array            | Target | Expected | What it checks              |
|------|------------------|--------|----------|-----------------------------|
| 01   | 4 8 15 16 23     | 15     | 2        | found in the middle         |
| 02   | 4 8 15 16 23     | 4      | 0        | found first                 |
| 03   | 4 8 15 16 23     | 23     | 4        | found last                  |
| 04   | 4 8 15 16 23     | 42     | -1       | not found                   |
| 05   | 7                | 7      | 0        | n = 1                       |
| 06   | (empty)          | 3      | -1       | n = 0                       |
| 07   | 3 9 9 1 9 9      | 9      | 1        | duplicates: first match     |
| 08   | -5 0 -12 -5      | -12    | 2        | negative numbers            |

## Edge cases

`edge/` holds the inputs for the logical metric (`edge_case_runner`). There are
no `.out` files: the expected output comes from running `reference/search.c`.
The file name is the case name, and the reason shown for each case is in
`rules/search.json` under `"reasons"`.

| Case            | What it checks                                  |
|-----------------|-------------------------------------------------|
| n_zero          | empty array                                     |
| single_found    | one number, and it is the target                |
| single_missing  | one number, and it is not the target            |
| last_only       | the target is only in the last position         |
| all_duplicates  | every number is the target                      |
| int_limits      | INT_MAX and INT_MIN in the array                |
| target_is_n     | the target is equal to n                        |
| not_found_large | 1000 numbers, no match                          |
