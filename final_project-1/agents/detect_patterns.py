from typing import List, Dict
from collections import Counter
from game.engine.card import Card
from game.engine.hand_evaluator import HandEvaluator
import json
import os

HISTORY_FILE = "agent_stats.json"

def load_agent_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {
        "thresholds": {
            "raise_threshold": 0.665,
            "fold_threshold": 0.335,
            "bluff_alpha": 1.00,
            "accumulator": 0.000000
        },
        "round_stats": {
            "round_num": 0,
            "fold_count": 0,
            "call_count": 0,
            "raise_count": 0
        }
    }

def save_agent_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def evaluate_hand_pattern(hole: List[Card], board: List[Card]) -> Dict[str, bool]:
    cards = hole + board
    suits = [card.suit for card in cards]
    ranks = sorted(set(card.rank for card in cards))

    pattern = {
        "HIGHCARD": False,
        "ONEPAIR": False,
        "TWOPAIR": False,
        "THREECARD": False,
        "STRAIGHT": False,
        "FLASH": False,
        "FULLHOUSE": False,
        "FOURCARD": False,
        "STRAIGHTFLASH": False,
        "flush_draw": False,
        "open_ended": False,
        "gutshot": False,
        "top_pair": False,
        "mid_pair": False,
        "bottom_pair": False,
        "set": False,
        "overpair": False,
    }

    eval_info = HandEvaluator.gen_hand_rank_info(hole, board)
    hand_strength = eval_info["hand"]["strength"]
    if hand_strength in pattern:
        pattern[hand_strength] = True

    suit_counts = Counter(card.suit for card in cards)
    pattern["flush_draw"] = any(count == 4 for count in suit_counts.values())

    for i in range(len(ranks) - 3):
        window = ranks[i:i + 4]
        if window[-1] - window[0] == 3:
            pattern["open_ended"] = True
        elif window[-1] - window[0] <= 4:
            pattern["gutshot"] = True

    board_ranks = sorted(set(card.rank for card in board), reverse=True)
    if board_ranks:
        top = board_ranks[0]
        mid = board_ranks[len(board_ranks) // 2]
        bottom = board_ranks[-1]

        rank_counts = Counter(card.rank for card in cards)
        for rank, count in rank_counts.items():
            if count == 2:
                if rank == top:
                    pattern["top_pair"] = True
                elif rank == mid:
                    pattern["mid_pair"] = True
                elif rank == bottom:
                    pattern["bottom_pair"] = True
            elif count == 3:
                pattern["set"] = True

        hole_ranks = [card.rank for card in hole]
        if len(hole_ranks) == 2 and hole_ranks[0] == hole_ranks[1] and all(r > top for r in hole_ranks):
            pattern["overpair"] = True

    return pattern

