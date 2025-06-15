class PostflopDecisionEngine:
    def __init__(self, raise_threshold: float, fold_threshold: float):
        self.raise_threshold = raise_threshold
        self.fold_threshold = fold_threshold

    def adjust_thresholds(self, round_state, win: bool, stats: dict):
        n = stats["round_num"] + 1
        alpha = 0.1

        success_ratio = stats["raise_count"] / n if stats["raise_count"] > 0 else 0.5
        fail_ratio = stats["fold_count"] / n if stats["fold_count"] > 0 else 0.5

        self.raise_threshold = min(1.0, max(0.5,
            self.raise_threshold + alpha * (1 if win else -1) * success_ratio
        ))
        self.fold_threshold = min(0.5, max(0.1,
            self.fold_threshold - alpha * (1 if win else -1) * fail_ratio
        ))

