def lens_thermodynamic(R, A, D, L):
    # L is already distance from optimal noise, so M = R*A*D - L
    # R*A*D is "constructive work", L is "waste + mis-tuning"
    return (R * A * D) - L
