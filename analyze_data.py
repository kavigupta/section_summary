
import numpy as np
import pandas as pd

def get_columns(all_scores):
    cols,  = set(tuple(sorted(x)) for x in all_scores.values())
    return cols

def sanitize_scores(cols, scores):
    results = np.zeros(len(cols))
    for k, v in scores.items():
        results[cols.index(k)] = max(v.get('total', 0), v.get('effort', 0)) + max(v.get('composition', 0), v.get('revision', 0))
    return results

def remove_all_0s(data):
    return data.drop(data.agg('max')[data.agg('max') == 0].keys(), axis=1)

def to_frame(all_scores):
    cols = get_columns(all_scores)
    sanitized_scores = [(student, sanitize_scores(cols, scores)) for student, scores in all_scores.items()]
    data = pd.DataFrame([scores for _, scores in sanitized_scores],
                        index=[student for student, _ in sanitized_scores],
                        columns=cols)
    return remove_all_0s(data)

def by_cat(assign_type):
    return lambda x, cols: sum(val for col, val in zip(cols, x) if col.startswith(assign_type))

def recent_effort(row, cols):
    lab = hw = disc = 0
    for col, val in zip(cols, row):
        if col.startswith("disc"):
            disc = val
        if col.startswith("lab"):
            lab = val
        if col.startswith("hw"):
            hw = val
    return 2 * (disc + lab) + hw

def for_assignments(*assigns):
    def query(x, cols):
        for assign in assigns:
            if assign in cols:
                return x[cols.index(assign)]
        return 0
    return query

FINAL = ["final"]
MIDTERM_1 = ["mt1", "midterm1"]
MIDTERM_2 = ["mt2", "midterm2"]

def total(data):
    discussion = sum(data[col] for col in data if col[:4] == "disc")
    lab = sum(data[col] for col in data if col[:3] == "lab" and col[3] != 'c')
    labcheckoff = sum(data[col] for col in data if col[:4] == "labc")
    hw = sum(data[col] for col in data if col[:2] == "hw")
    proj = sum(data[col] for col in data if col[:4] == "proj" or "checkpoint" in col)
    mt1 = data.midterm1 + data.midterm1extra
    mt2 = data.midterm2

    def midterm_recovery(score, recovery, max_score):
        half_score = max_score / 2
        max_recovery = (half_score - score).clip(0, 10000) / 2
        return score + pd.DataFrame([recovery, max_recovery]).min(0)

    participation = discussion + lab + labcheckoff
    particip_points = participation.clip(0, 10)
    particip_recovery = participation.clip(10, 30) - 10

    recovered_mt1 = midterm_recovery(mt1, particip_recovery, 40)
    recovered_mt2 = midterm_recovery(mt2, particip_recovery, 50)

    final = 0 # not released

    return recovered_mt1 + recovered_mt2 + final + proj + hw + particip_points

QUERIES = [
    ("final", for_assignments(*FINAL)),
    ("midterm 2", for_assignments(*MIDTERM_2)),
    ("midterm 1", for_assignments(*MIDTERM_1)),
    ("proj", by_cat("proj")),
    ("disc", by_cat("disc")),
    ("lab", by_cat("lab")),
    ("hw", by_cat("hw")),
    ("recent effort", recent_effort)
]

def matches_exam(column):
    result = False
    for exam in FINAL + MIDTERM_1 + MIDTERM_2:
        result |= column == exam
    return result

def run_queries(data):
    queries = np.array([list(data.apply(lambda x: fn(x, list(data.columns)), axis=1)) for _, fn in QUERIES]).T
    without_exams = data[data.columns[~matches_exam(data.columns)]]
    frame = pd.DataFrame(np.concatenate([np.array([total(data)]).T, queries, without_exams], axis=1),
                         index=data.index, columns=["Total"] + [x for x, _ in QUERIES] + list(without_exams.columns))
    frame = remove_all_0s(frame)
    return frame.sort_values(list(frame.columns))
