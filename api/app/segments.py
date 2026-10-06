"""RFM segments: named groups of customers, decided by their R and FM scores.

Each customer has three scores from 1 (worst) to 5 (best), ranked against the
organization's other customers:
    R  recency    how recently they last ordered
    F  frequency  how many orders they have placed
    M  monetary   how much they have spent in total
F and M are averaged (rounded up) into one "FM" value, because in practice
they move together: customers who order often also spend more.

The rules below are checked from the top; the first match names the segment.
Together they cover every possible combination of R and FM exactly once.
"""

# (segment, lowest R, highest R, lowest FM, highest FM)
RULES = [
    ("Champions", 4, 5, 4, 5),  # bought recently, buy often, spend the most
    ("Loyal", 3, 3, 4, 5),  # strong buyers, slightly less recent
    ("Potential loyalists", 4, 5, 2, 3),  # recent, with middling spend so far
    ("New", 4, 5, 1, 1),  # recent, but have bought little so far
    ("Need attention", 3, 3, 1, 3),  # neither recent nor strong
    ("Can't lose them", 1, 2, 5, 5),  # used to be among the best, gone quiet
    ("At risk", 1, 2, 3, 4),  # used to buy well, gone quiet
    ("Lost", 1, 2, 1, 2),  # long gone, never bought much
]

# The order segments are listed in on screen: best first. The web app colours
# them in this order (web/src/lib/segments.ts), the same colour on every screen.
SEGMENTS = [
    "Champions",
    "Loyal",
    "Potential loyalists",
    "New",
    "Need attention",
    "At risk",
    "Can't lose them",
    "Lost",
]


def fm_score(f: int, m: int) -> int:
    return (f + m + 1) // 2


def segment_for(r: int, f: int, m: int) -> str:
    fm = fm_score(f, m)
    for name, r_low, r_high, fm_low, fm_high in RULES:
        if r_low <= r <= r_high and fm_low <= fm <= fm_high:
            return name
    raise ValueError(f"No segment for R={r} F={f} M={m}")


def segment_case_sql(r: str, f: str, m: str) -> str:
    """The same rules as a SQL CASE expression, for use inside the metrics query.
    The arguments are SQL expressions for the three scores."""
    fm = f"(({f} + {m} + 1) / 2)"  # integer division in SQL, like fm_score()
    lines = ["CASE"]
    for name, r_low, r_high, fm_low, fm_high in RULES:
        quoted = "'" + name.replace("'", "''") + "'"  # SQL escapes ' by doubling it
        lines.append(
            f"  WHEN {r} BETWEEN {r_low} AND {r_high} AND {fm} BETWEEN {fm_low} AND {fm_high} "
            f"THEN {quoted}"
        )
    lines.append("END")
    return "\n".join(lines)
