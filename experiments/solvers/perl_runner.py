"""
╔════════════════════════════════════════════════════════════════╗
║ ECOLOGICAL INTELLIGENCE ARCHITECTURE                           ║
║                                                                ║
║ This system is NOT a central controller making decisions.      ║
║ It is a distributed ecology of specialized solvers (cells)     ║
║ organized by a learned topology (landscape) that reads signals ║
║ (waste, latency, overhead) and routes work accordingly.        ║
║                                                                ║
║ • Each runner: one specialized function                        ║
║ • Dispatcher: a router reading cell signals, not a thinker     ║
║ • Landscape: topology learned from observed flows              ║
║ • Waste audit: how cells talk back to the router               ║
║                                                                ║
║ Intelligence emerges from specialization + signal flow +       ║
║ topology learning. Not from central control.                   ║
╚════════════════════════════════════════════════════════════════╝

ROLE: CELL -- Pollard-rho factoring specialist (Perl bigint). Emits wall-time + overhead signals.

solvers/perl_runner.py -- Pollard rho via perl.

Perl's fit: text-stream processing, regex, glue-code. Numeric tight
loops are NOT its native habitat -- interesting to see how it loses
on (bit, num) axes vs C.

Graceful skip if perl not installed.
"""
from __future__ import annotations
import subprocess, sys, os, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner_api import Problem, register_runner

PERL_POLLARD = r'''
use strict; use warnings;
use bigint;
my $n = $ARGV[0] + 0;
sub gcd { my ($a, $b) = @_; ($a, $b) = ($b, $a % $b) while $b; return $a; }
sub pollard {
    my $n = shift;
    return 2 if $n % 2 == 0;
    while (1) {
        my $x = 2; my $y = 2; my $c = int(rand(100)) + 1; my $d = 1;
        while ($d == 1) {
            $x = (($x * $x) + $c) % $n;
            $y = (($y * $y) + $c) % $n;
            $y = (($y * $y) + $c) % $n;
            my $diff = $x > $y ? $x - $y : $y - $x;
            $d = gcd($diff, $n);
        }
        return $d if $d != $n;
    }
}
my $f = pollard($n);
print "$f ", ($n / $f), "\n";
'''

FACTOR_TAG_HINT = {"bignum", "bitwise", "numeric_tight"}

def _name_matches(problem_name: str, family: str) -> bool:
    return problem_name == family or problem_name.startswith(family + "_")

def _tags_consistent(problem: Problem) -> bool:
    return bool({t.value for t in problem.tags} & FACTOR_TAG_HINT)

@register_runner("perl")
def run_perl(problem: Problem) -> tuple[bool, str, float]:
    if not _name_matches(problem.name, "factor"):
        return False, f"no perl solver for '{problem.name}'", 0.0
    if not _tags_consistent(problem):
        return False, "factor: tags don't include bignum/bitwise/numeric_tight", 0.0
    if not shutil.which("perl"):
        return False, "perl not available", 0.0
    if "n" not in problem.payload:
        return False, "factor: missing required payload key 'n'", 0.0
    n = problem.payload["n"]
    if not isinstance(n, int) or n < 4:
        return False, f"factor: invalid n={n!r}", 0.0

    r = subprocess.run(["perl", "-e", PERL_POLLARD, str(n)],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return False, f"perl run failed: {r.stderr}", 0.0
    try:
        a_s, b_s = r.stdout.strip().split()
        a, b = int(a_s), int(b_s)
    except Exception as e:
        return False, f"perl output parse failed: {e!r}; stdout={r.stdout!r}", 0.0
    if a <= 1 or a >= n or a * b != n:
        return False, f"factor: bogus perl result f={a} for n={n}", 0.0
    return True, f"{n} = {a} * {b}", 0.0
