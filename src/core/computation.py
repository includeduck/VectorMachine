sp = None
parse_expr = None
standard_transformations = None
implicit_multiplication_application = None
np = None

x, y, z = None, None, None
local_dict = None

def _lazy_init():
    global sp, parse_expr, standard_transformations, implicit_multiplication_application, np
    global x, y, z, local_dict
    
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
    local_dict = {'x': x, 'y': y, 'z': z}

def parse_expression(expr_str):
    """
    Parses a string into a SymPy expression.
    Returns (expr, None) on success, or (None, error_message) on failure.
    """
    if not expr_str or not expr_str.strip():
        return None, "Expression cannot be empty."
        
    _lazy_init()
    try:
        transformations = standard_transformations + (implicit_multiplication_application,)
        expr = parse_expr(expr_str, local_dict=local_dict, transformations=transformations)
        return expr, None
    except Exception as e:
        return None, f"Syntax Error: {str(e)}"

def compute_divergence(P_expr, Q_expr, R_expr):
    """
    Computes divergence of a vector field F = <P, Q, R>.
    Returns a dictionary with step-by-step results.
    """
    _lazy_init()
    dP_dx = sp.diff(P_expr, x)
    dQ_dy = sp.diff(Q_expr, y)
    dR_dz = sp.diff(R_expr, z)
    div_expr = sp.simplify(dP_dx + dQ_dy + dR_dz)
    
    steps = {
        "dP_dx": str(dP_dx),
        "dQ_dy": str(dQ_dy),
        "dR_dz": str(dR_dz),
        "formula": "∂P/∂x + ∂Q/∂y + ∂R/∂z",
        "unsimplified": str(dP_dx + dQ_dy + dR_dz),
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
    _lazy_init()
    # lambdify the expressions. We provide 'numpy' to use numpy functions for sin, cos, exp etc.
    p_func = sp.lambdify((x, y, z), P_expr, modules='numpy')
    q_func = sp.lambdify((x, y, z), Q_expr, modules='numpy')
    r_func = sp.lambdify((x, y, z), R_expr, modules='numpy')
    
    # Evaluate over the grids. If an expression is a constant (like 'z' derivative might be 0),
    # lambdify might return a scalar. We use np.broadcast_to to ensure it's an array of grid shape.
    u = p_func(x_grid, y_grid, z_grid)
    v = q_func(x_grid, y_grid, z_grid)
    w = r_func(x_grid, y_grid, z_grid)
    
    u = np.broadcast_to(np.asarray(u), x_grid.shape)
    v = np.broadcast_to(np.asarray(v), x_grid.shape)
    w = np.broadcast_to(np.asarray(w), x_grid.shape)
    
    return u, v, w
