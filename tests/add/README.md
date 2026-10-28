# Tests for add_two_integers

Each test is a pair of files: `NN.in` is fed to the program on standard input,
and `NN.out` is the output we expect (the sum followed by a newline).

| Test | Input                    | Expected    | What it checks                          |
|------|--------------------------|-------------|-----------------------------------------|
| 01   | 7 5                      | 12          | the sample from the brief               |
| 02   | 0 0                      | 0           | zero                                    |
| 03   | -3 -4                    | -7          | two negatives                           |
| 04   | -10 4                    | -6          | mixed signs                             |
| 05   | 100000 200000            | 300000      | larger numbers                          |
| 06   | 2147483647 0             | 2147483647  | INT_MAX, no overflow yet                |
| 07   | 2147483647 1             | 2147483648  | sum goes above INT_MAX                  |
| 08   | -2147483648 -1           | -2147483649 | sum goes below INT_MIN                  |
| 09   | `   12     30   `         | 42          | extra spaces around the numbers         |
| 10   | -2147483648 2147483647   | -1          | both limits, but the sum fits in an int |

## Decisions we made

1. The expected output for `2147483647 1` is `2147483648`, the true sum.
   The brief's example report shows `-2147483648`, but that is the value you
   get after the overflow, not the sum. The problem says "print their sum",
   and the brief itself lists INT_MAX + 1 as a weakness of the sample code.
   Also, in C, signed overflow is undefined behaviour, so `-2147483648` is
   not even guaranteed. A student who uses `long long` should pass, so we
   treat the true sum as correct. Test 08 is the same idea at the bottom end.

2. The brief's sample input is printed as "75". We read it as "7 5", because
   the problem says two integers separated by whitespace and the sample
   output is 12.

With these tests, the brief's add.c passes 8 of 10 (it fails 07 and 08),
which matches the "8 of 10 tests pass" in the brief's example.
