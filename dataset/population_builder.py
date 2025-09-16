from math import exp
from random import choices

def build_population(allow_4: bool) -> int:
    mu = 2.0
    sigma = 1.0
    values = [1, 2, 3, 4] if allow_4 else [1, 2, 3]
    weights = [exp(-((v - mu) ** 2) / (2 * (sigma ** 2))) for v in values]
    return choices(values, weights=weights, k=1)[0]
