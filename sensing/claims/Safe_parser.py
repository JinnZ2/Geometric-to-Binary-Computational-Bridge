#!/usr/bin/env python3
"""
safe_parser.py — AST-based safe evaluator for claim predicates.

Replaces `eval()` with a restricted Abstract Syntax Tree walker.
Only allows:
- Variables: 'u', 'omega', 'uncertainty', and any keys in `context_extra`.
- Operations: arithmetic (+, -, *, /), comparison (<, >, <=, >=, ==, !=), logical (and, or, not).
- Literals: numbers, True, False, None.
"""

import ast
import operator
import math
from typing import Any, Dict, List, Set, Optional

# ---------- Allowed operations ----------
ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.And: lambda a, b: a and b,
    ast.Or: lambda a, b: a or b,
    ast.Not: operator.not_,
    ast.IfExp: lambda cond, t, f: t if cond else f,  # ternary
}

ALLOWED_NODE_TYPES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Compare,
    ast.BoolOp, ast.IfExp, ast.Name, ast.Constant,
    ast.Load, ast.List, ast.Tuple, ast.Dict, ast.Subscript,
    ast.Attribute, ast.Index, ast.Slice, ast.Call, ast.keyword,
)

# ---------- Safe evaluator ----------
class SafeEvaluator(ast.NodeVisitor):
    def __init__(self, locals_dict: Dict[str, Any]):
        self.locals = locals_dict
        self._allowed_names = set(locals_dict.keys()) | {"True", "False", "None", "abs", "len", "min", "max", "sum", "math"}
        self._math = math  # for math functions like sin, cos
    
    def visit(self, node):
        if not isinstance(node, ALLOWED_NODE_TYPES):
            raise ValueError(f"Disallowed node type: {type(node).__name__}")
        return super().visit(node)
    
    def visit_Constant(self, node: ast.Constant):
        return node.value
    
    def visit_Name(self, node: ast.Name):
        if node.id not in self._allowed_names:
            # Check if it's in the locals dict (e.g., context keys)
            if node.id in self.locals:
                return self.locals[node.id]
            # Check if it's a math attribute
            if node.id in dir(math):
                return getattr(math, node.id)
            raise ValueError(f"Variable '{node.id}' not allowed or not in context.")
        if node.id == "True": return True
        if node.id == "False": return False
        if node.id == "None": return None
        if node.id == "math": return math
        return self.locals.get(node.id, None)
    
    def visit_Attribute(self, node: ast.Attribute):
        # Allow u[0], u[1] via Subscript, but we also allow direct attributes like u.shape
        obj = self.visit(node.value)
        if isinstance(obj, (list, tuple, np.ndarray)):
            # If it's a sequence, attribute access is not supported; only indexing.
            # But we can allow .shape for arrays, etc.
            if hasattr(obj, node.attr):
                return getattr(obj, node.attr)
            raise ValueError(f"Attribute '{node.attr}' not allowed on type {type(obj)}.")
        if hasattr(obj, node.attr):
            return getattr(obj, node.attr)
        raise ValueError(f"Attribute '{node.attr}' not found on {obj}")
    
    def visit_Subscript(self, node: ast.Subscript):
        obj = self.visit(node.value)
        if isinstance(node.slice, ast.Index):
            idx = self.visit(node.slice.value)
        elif isinstance(node.slice, ast.Slice):
            # For slices, we need to handle carefully
            lower = self.visit(node.slice.lower) if node.slice.lower else None
            upper = self.visit(node.slice.upper) if node.slice.upper else None
            step = self.visit(node.slice.step) if node.slice.step else None
            return obj[lower:upper:step]
        else:
            idx = self.visit(node.slice)
        return obj[idx]
    
    def visit_BinOp(self, node: ast.BinOp):
        left = self.visit(node.left)
        right = self.visit(node.right)
        op_type = type(node.op)
        if op_type not in ALLOWED_OPERATORS:
            raise ValueError(f"Binary operator {op_type.__name__} not allowed.")
        return ALLOWED_OPERATORS[op_type](left, right)
    
    def visit_UnaryOp(self, node: ast.UnaryOp):
        operand = self.visit(node.operand)
        op_type = type(node.op)
        if op_type not in ALLOWED_OPERATORS:
            raise ValueError(f"Unary operator {op_type.__name__} not allowed.")
        return ALLOWED_OPERATORS[op_type](operand)
    
    def visit_Compare(self, node: ast.Compare):
        left = self.visit(node.left)
        results = []
        for op, comp in zip(node.ops, node.comparators):
            right = self.visit(comp)
            op_type = type(op)
            if op_type not in ALLOWED_OPERATORS:
                raise ValueError(f"Comparison {op_type.__name__} not allowed.")
            results.append(ALLOWED_OPERATORS[op_type](left, right))
            left = right
        return all(results)
    
    def visit_BoolOp(self, node: ast.BoolOp):
        values = [self.visit(v) for v in node.values]
        op_type = type(node.op)
        if op_type not in ALLOWED_OPERATORS:
            raise ValueError(f"Boolean operator {op_type.__name__} not allowed.")
        # Reduce using the operator
        result = values[0]
        for v in values[1:]:
            result = ALLOWED_OPERATORS[op_type](result, v)
        return result
    
    def visit_IfExp(self, node: ast.IfExp):
        cond = self.visit(node.test)
        return self.visit(node.body) if cond else self.visit(node.orelse)
    
    def visit_Call(self, node: ast.Call):
        # Only allow specific built-ins and math functions
        func = self.visit(node.func)
        if func not in (abs, len, min, max, sum) and not hasattr(math, func.__name__):
            raise ValueError(f"Function call to '{func}' not allowed.")
        args = [self.visit(a) for a in node.args]
        kwargs = {kw.arg: self.visit(kw.value) for kw in node.keywords}
        return func(*args, **kwargs)
    
    def visit_List(self, node: ast.List):
        return [self.visit(elt) for elt in node.elts]
    
    def visit_Tuple(self, node: ast.Tuple):
        return tuple(self.visit(elt) for elt in node.elts)
    
    def visit_Dict(self, node: ast.Dict):
        return {self.visit(k): self.visit(v) for k, v in zip(node.keys, node.values)}
    
    def generic_visit(self, node):
        raise ValueError(f"Unsupported node type: {type(node).__name__}")


def safe_evaluate(condition_str: str, context: Dict[str, Any]) -> bool:
    """
    Safely evaluate a condition string using the restricted AST parser.
    
    Args:
        condition_str: e.g., "u[1] < 0.0 and omega > 0.5"
        context: dict containing 'u', 'omega', 'uncertainty', and any extra variables.
    
    Returns:
        Boolean result.
    """
    try:
        tree = ast.parse(condition_str, mode="eval")
        evaluator = SafeEvaluator(context)
        result = evaluator.visit(tree.body)
        return bool(result)
    except Exception as e:
        raise ValueError(f"Failed to evaluate condition '{condition_str}': {e}")
