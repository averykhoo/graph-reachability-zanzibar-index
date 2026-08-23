#!/usr/bin/env python
"""Mann-Whitney U for the task-tool trial, with the exact small-n critical values.

Deliberately NOT scipy: this runs on the repo's declared deps (none of which is scipy),
and at n=6 the exact critical value is a table lookup, not a computation worth a
dependency.

WHY U AND NOT A t-TEST: n=6 per arm, no reason to believe normality, and the token
distributions are visibly tight-with-a-floor rather than bell-shaped. U asks only whether
one arm's values tend to rank above the other's, which is the entire claim being made.

WHY THE CRITICAL VALUE IS A LITERAL TABLE: the normal approximation is wrong at n=6 -- it
is the reason an underpowered comparison can be reported as significant -- so the exact
two-tailed alpha=0.05 critical U is hardcoded for the n actually run, and any other n
REFUSES rather than falling back to the approximation.
"""
from __future__ import print_function
import sys

# Exact two-tailed alpha=0.05 critical values for Mann-Whitney U. Reject H0 when U <= crit.
# Only the shapes this trial actually runs are listed; anything else must refuse rather
# than silently approximate.
CRIT_05 = {(6, 6): 5, (3, 3): None, (5, 6): 3, (6, 5): 3, (4, 6): 2, (6, 4): 2}


def mannwhitney(a, b):
    """U for sample `a` against `b`, tie-corrected by mid-ranks."""
    pooled = sorted([(v, 0) for v in a] + [(v, 1) for v in b])
    ranks = [0.0] * len(pooled)
    i = 0
    while i < len(pooled):
        j = i
        while j + 1 < len(pooled) and pooled[j + 1][0] == pooled[i][0]:
            j += 1
        mid = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            ranks[k] = mid
        i = j + 1
    r_a = sum(r for r, (_, g) in zip(ranks, pooled) if g == 0)
    n1, n2 = len(a), len(b)
    u_a = r_a - n1 * (n1 + 1) / 2.0
    return min(u_a, n1 * n2 - u_a)


def med(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def report(name, board, tree):
    print('== %s ==' % name)
    print('  BOARD n=%d  median %9.1f  range %s..%s' % (len(board), med(board), min(board), max(board)))
    print('  TREE  n=%d  median %9.1f  range %s..%s' % (len(tree), med(tree), min(tree), max(tree)))
    d = med(board) - med(tree)
    print('  difference in medians: %.1f  (TREE is %.1f%% of BOARD)'
          % (d, 100.0 * med(tree) / med(board) if med(board) else float('nan')))
    key = (len(board), len(tree))
    crit = CRIT_05.get(key, 'ABSENT')
    u = mannwhitney(board, tree)
    if crit == 'ABSENT':
        print('  U=%.1f -- REFUSED: no exact critical value tabled for n=%d vs %d. Add it '
              'or report descriptively; the normal approximation is not valid here.'
              % (u, len(board), len(tree)))
    elif crit is None:
        print('  U=%.1f -- NO TEST: at n=%d vs %d the smallest attainable two-tailed p '
              'exceeds 0.05, so NO arrangement of these data could reach significance. '
              'Descriptive only, by design.' % (u, len(board), len(tree)))
    else:
        verdict = 'REJECT H0 (p<0.05)' if u <= crit else 'fail to reject H0'
        print('  U=%.1f  critical U(two-tailed, .05)=%d  ->  %s' % (u, crit, verdict))
    print('')


if __name__ == '__main__':
    print('usage: import and call report(); values are pasted in by the analysis step')
    sys.exit(0)
