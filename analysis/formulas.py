def speedup(t1: float, tn: float) -> float:
    return t1 / tn

def workers_for_arrival_rate(lam: float, t: float, c: float) -> int:
    # N ≈ λ·T / C
    return max(1, math.ceil((lam * t) / c))

def workers_for_backlog(B: int, lam: float, Tr: float, C: float) -> int:
    # N ≥ (B/Tr + λ) / C
    return max(1, math.ceil((B/Tr + lam) / C))
