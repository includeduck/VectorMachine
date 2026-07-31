import re
from collections import OrderedDict

sp = None
parse_expr = None
standard_transformations = None
implicit_multiplication_application = None
np = None

x, y, z = None, None, None
local_dict = None
_safe_global_dict = None
_lambdify_cache = OrderedDict()
_LAMBDA_CACHE_LIMIT = 128

_SUPPORTED_IDENTIFIERS = frozenset({
    "x", "y", "z", "E", "pi",
    "sin", "cos", "tan", "asin", "acos", "atan", "atan2",
    "sinh", "cosh", "tanh", "asinh", "acosh", "atanh",
    "exp", "sqrt", "log", "ln", "Abs", "sign", "floor", "ceiling",
})
_IDENTIFIER_RE = re.compile(r"[A-Za-z_]\w*")
_ALLOWED_CHARACTER_RE = re.compile(r"^[0-9A-Za-z_+\-*/^().,!\s]*$")

def _lazy_init():
    global sp, parse_expr, standard_transformations, implicit_multiplication_application, np
    global x, y, z, local_dict, _safe_global_dict
    
    if sp is not None:
        return
        
    import sympy as _sp
    from sympy.parsing.sympy_parser import parse_expr as _pe, standard_transformations as _st, implicit_multiplication_application as _ima
    import numpy as _np
    
    sp = _sp
    parse_expr = _pe
    standard_transformations = _st
    implicit_multiplication_application = _ima
    np = _np
    
    x, y, z = sp.symbols('x y z')
    local_dict = {
        'x': x, 'y': y, 'z': z,
        'E': sp.E, 'pi': sp.pi,
        'sin': sp.sin, 'cos': sp.cos, 'tan': sp.tan,
        'asin': sp.asin, 'acos': sp.acos, 'atan': sp.atan, 'atan2': sp.atan2,
        'sinh': sp.sinh, 'cosh': sp.cosh, 'tanh': sp.tanh,
        'asinh': sp.asinh, 'acosh': sp.acosh, 'atanh': sp.atanh,
        'exp': sp.exp, 'sqrt': sp.sqrt, 'log': sp.log, 'ln': sp.log,
        'Abs': sp.Abs, 'sign': sp.sign, 'floor': sp.floor, 'ceiling': sp.ceiling,
    }
    # ``parse_expr`` ultimately evaluates generated Python code.  Keep its
    # execution namespace deliberately small and free of builtins.
    _safe_global_dict = {
        '__builtins__': {},
        'Integer': sp.Integer,
        'Float': sp.Float,
        'Rational': sp.Rational,
        'factorial': sp.factorial,
    }

def parse_expression(expr_str):
    """
    Parses a string into a SymPy expression.
    Returns (expr, None) on success, or (None, error_message) on failure.
    """
    if not isinstance(expr_str, str):
        return None, "Expression must be text."
    if not expr_str or not expr_str.strip():
        return None, "Expression cannot be empty."

    _lazy_init()

    expression = expr_str.strip()
    if not _ALLOWED_CHARACTER_RE.fullmatch(expression):
        return None, "Expression contains unsupported characters."

    identifiers = _IDENTIFIER_RE.findall(expression)
    unknown_identifiers = [
        name for name in identifiers
        if name not in _SUPPORTED_IDENTIFIERS and not set(name) <= {"x", "y", "z"}
    ]
    if unknown_identifiers:
        return None, f"Unsupported name: {unknown_identifiers[0]}."

    try:
        transformations = standard_transformations + (implicit_multiplication_application,)
        expr = parse_expr(
            expression,
            local_dict=local_dict.copy(),
            global_dict=_safe_global_dict.copy(),
            transformations=transformations,
        )
        if not isinstance(expr, sp.Expr) or not expr.free_symbols <= {x, y, z}:
            return None, "Expression must use only x, y, and z."
        return expr, None
    except Exception as e:
        return None, f"Syntax Error: {str(e)}"

def _get_lambdified(expressions):
    """Return one cached NumPy function for all three field components."""
    key = tuple(expressions)
    try:
        func = _lambdify_cache.pop(key)
    except KeyError:
        func = sp.lambdify((x, y, z), key, modules='numpy')
        if len(_lambdify_cache) >= _LAMBDA_CACHE_LIMIT:
            _lambdify_cache.popitem(last=False)
    _lambdify_cache[key] = func
    return func

def compute_divergence(P_expr, Q_expr, R_expr):
    """
    Computes divergence of a vector field F = <P, Q, R>.
    Returns a dictionary with step-by-step results.
    """
    _lazy_init()
    dP_dx = sp.diff(P_expr, x)
    dQ_dy = sp.diff(Q_expr, y)
    dR_dz = sp.diff(R_expr, z)
    unsimplified = dP_dx + dQ_dy + dR_dz
    div_expr = sp.simplify(unsimplified)
    
    steps = {
        "dP_dx": str(dP_dx),
        "dQ_dy": str(dQ_dy),
        "dR_dz": str(dR_dz),
        "formula": "∂P/∂x + ∂Q/∂y + ∂R/∂z",
        "unsimplified": str(unsimplified),
        "final": str(div_expr)
    }
    return steps

def compute_curl(P_expr, Q_expr, R_expr):
    """
    Computes curl of a vector field F = <P, Q, R>.
    Returns a dictionary with step-by-step results.
    """
    _lazy_init()
    dR_dy = sp.diff(R_expr, y)
    dQ_dz = sp.diff(Q_expr, z)
    i_comp_unsimplified = dR_dy - dQ_dz
    i_comp = sp.simplify(i_comp_unsimplified)
    
    dP_dz = sp.diff(P_expr, z)
    dR_dx = sp.diff(R_expr, x)
    j_comp_unsimplified = dP_dz - dR_dx
    j_comp = sp.simplify(j_comp_unsimplified)
    
    dQ_dx = sp.diff(Q_expr, x)
    dP_dy = sp.diff(P_expr, y)
    k_comp_unsimplified = dQ_dx - dP_dy
    k_comp = sp.simplify(k_comp_unsimplified)
    
    steps = {
        "dR_dy": str(dR_dy),
        "dQ_dz": str(dQ_dz),
        "dP_dz": str(dP_dz),
        "dR_dx": str(dR_dx),
        "dQ_dx": str(dQ_dx),
        "dP_dy": str(dP_dy),
        "i_comp_unsimplified": str(i_comp_unsimplified),
        "j_comp_unsimplified": str(j_comp_unsimplified),
        "k_comp_unsimplified": str(k_comp_unsimplified),
        "i_comp": str(i_comp),
        "j_comp": str(j_comp),
        "k_comp": str(k_comp),
        "final_i": str(i_comp),
        "final_j": str(j_comp),
        "final_k": str(k_comp)
    }
    return steps

def evaluate_field(P_expr, Q_expr, R_expr, x_grid, y_grid, z_grid):
    """
    Evaluates the vector field <P, Q, R> over a numpy meshgrid.
    Returns u, v, w as numpy arrays.
    """
    import time
    from src.core.debug_log import debug_log

    _lazy_init()
    t0 = time.perf_counter()
    field_func = _get_lambdified((P_expr, Q_expr, R_expr))
    lambdify_ms = (time.perf_counter() - t0) * 1000

    with np.errstate(all="ignore"):
        u, v, w = field_func(x_grid, y_grid, z_grid)

    components = []
    for component in (u, v, w):
        array = np.broadcast_to(np.asarray(component), x_grid.shape)
        if not np.issubdtype(array.dtype, np.number):
            raise ValueError("Field components must evaluate to numeric values.")
        components.append(array)
    u, v, w = components

    debug_log(
        "computation.py:evaluate_field",
        "field evaluated",
        {
            "lambdifyMs": round(lambdify_ms, 2),
            "cacheSize": len(_lambdify_cache),
            "gridPoints": int(x_grid.size),
        },
        "E",
    )
    
    return u, v, w

def clear_lambdify_cache():
    _lambdify_cache.clear()
