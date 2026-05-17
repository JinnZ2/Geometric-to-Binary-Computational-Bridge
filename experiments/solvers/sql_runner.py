"""solvers/sql_runner.py — relational puzzle solver via sqlite3 stdlib.

Demonstrates: the SHAPE of a problem determines the language.
N-queens is a constraint-satisfaction / relational problem — SQL is native fit.
"""solvers/sql_runner.py -- relational puzzle solver via sqlite3 stdlib.

╔════════════════════════════════════════════════════════════════╗
║ ECOLOGICAL INTELLIGENCE ARCHITECTURE                           ║
║                                                                ║
║ This file is a specialized CELL in a distributed ecology.      ║
║ It does ONE thing: solves relational/constraint problems via   ║
║ SQL recursive CTEs, in-process (no subprocess overhead).       ║
║                                                                ║
║ SQL's native habitat is set/join semantics. The landscape      ║
║ learns from races: priors said SQL would win n-queens, reality ║
║ said Python's backtracking is ~100x faster at small board      ║
║ sizes. The topology absorbed that signal -- that's the loop.   ║
╚════════════════════════════════════════════════════════════════╝

Demonstrates: the SHAPE of a problem determines the language.
N-queens is a constraint-satisfaction / relational problem -- SQL is native fit.
No subprocess overhead: sqlite3 is in-process.
"""
from __future__ import annotations
import sqlite3, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner_api import Problem, register_runner


N_QUEENS_SQL = """
WITH RECURSIVE
cols(c) AS (
    SELECT 1
    UNION ALL
    SELECT c + 1 FROM cols WHERE c < ?
),
-- place(row, col_list_as_text)
-- col_list is a comma-separated list of columns already placed, row-by-row
place(row, cols_used) AS (
N_QUEENS_SQL = """
WITH RECURSIVE
  cols(c) AS (
    SELECT 1
    UNION ALL
    SELECT c + 1 FROM cols WHERE c < ?
  ),
  -- place(row, col_list_as_text)
  -- col_list is a comma-separated list of columns already placed, row-by-row
  place(row, cols_used) AS (
    -- base: row 1, any column
    SELECT 1, CAST(c AS TEXT) FROM cols
    UNION ALL
    -- extend: for each partial placement of length `row`, try every column for row+1
    -- that doesn't violate column / diagonal constraints
    SELECT p.row + 1,
           p.cols_used || ',' || CAST(c.c AS TEXT)
    FROM place p, cols c
    WHERE p.row < ?
      AND NOT EXISTS (
          -- check column conflict + diagonal conflict against each prior row
          SELECT 1 FROM (
              WITH RECURSIVE split(i, val, rest) AS (
                  SELECT 1,
                         CAST(substr(p.cols_used || ',', 1,
                                     instr(p.cols_used || ',', ',') - 1) AS INTEGER),
                         substr(p.cols_used || ',', instr(p.cols_used || ',', ',') + 1)
                  UNION ALL
                  SELECT i + 1,
                         CAST(substr(rest, 1, instr(rest, ',') - 1) AS INTEGER),
                         substr(rest, instr(rest, ',') + 1)
                  FROM split WHERE rest != ''
              )
              SELECT 1 FROM split
              WHERE val = c.c                                -- same column
                 OR abs(val - c.c) = abs(i - (p.row + 1))    -- same diagonal
          )
      )
)
        -- check column conflict + diagonal conflict against each prior row
        SELECT 1 FROM (
          WITH RECURSIVE split(i, val, rest) AS (
            SELECT 1,
                   CAST(substr(p.cols_used || ',', 1,
                        instr(p.cols_used || ',', ',') - 1) AS INTEGER),
                   substr(p.cols_used || ',', instr(p.cols_used || ',', ',') + 1)
            UNION ALL
            SELECT i + 1,
                   CAST(substr(rest, 1, instr(rest, ',') - 1) AS INTEGER),
                   substr(rest, instr(rest, ',') + 1)
            FROM split WHERE rest != ''
          )
          SELECT 1 FROM split
          WHERE val = c.c                                -- same column
             OR abs(val - c.c) = abs(i - (p.row + 1))    -- same diagonal
        )
      )
  )
SELECT cols_used FROM place WHERE row = ?
LIMIT ?;
"""


def _solve_nqueens(n: int, limit: int = 10) -> list[list[int]]:
    """Returns up to `limit` solutions as column-lists per row."""
    conn = sqlite3.connect(":memory:")
    try:
        rows = conn.execute(N_QUEENS_SQL, (n, n, n, limit)).fetchall()
        return [[int(x) for x in r[0].split(",")] for r in rows]
    finally:
        conn.close()


def _name_matches(problem_name: str, family: str) -> bool:
    return problem_name == family or problem_name.startswith(family + "_")


@register_runner("sql")
def run_sql(problem: Problem) -> tuple[bool, str, float]:
    if _name_matches(problem.name, "nqueens"):
        if "n" not in problem.payload:
            return False, "nqueens: missing required payload key 'n'", 0.0
        n = problem.payload["n"]
        if not isinstance(n, int) or n < 1:
            return False, f"nqueens: n must be positive int, got {n!r}", 0.0
        limit = problem.payload.get("limit", 5)
        if not isinstance(limit, int) or limit < 1:
            return False, f"nqueens: limit must be positive int, got {limit!r}", 0.0
        sols = _solve_nqueens(n, limit=limit)
        if not sols:
            return False, f"nqueens: no solutions for n={n}", 0.0
        return True, f"n={n}, found {len(sols)} solution(s); first: {sols[0]}", 0.0
    return False, f"no SQL solver for '{problem.name}'", 0.0
