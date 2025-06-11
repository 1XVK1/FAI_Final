import random
import json
import os
import game.visualize_utils as U
from game.players import BasePokerPlayer
from agents.MCS import Starting_Hand_WR, river_WR_test, monte_carlo_win_rate
from game.engine.card import Card


class RLPolicy:
    def __init__(self, qtable_file="qtable.json"):
        self.qtable_file = qtable_file
        self.ensure_qtable_file()
        self.q_table = self.load_qtable()
        self.alpha = 0.1
        self.gamma = 0.9
        self.epsilon = 0.1

    def ensure_qtable_file(self):
        if not os.path.exists(self.qtable_file):
            with open(self.qtable_file, "w") as f:
                json.dump({}, f)

    def load_qtable(self):
        if os.path.getsize(self.qtable_file) == 0:
            with open(self.qtable_file, "w") as f:
                json.dump({}, f)
        with open(self.qtable_file, "r") as f:
            return json.load(f)

    def save_qtable(self):
        with open(self.qtable_file, "w") as f:
            json.dump(self.q_table, f)

    def get_action(self, state, valid_actions):
        if state not in self.q_table:
            self.q_table[state] = {a["action"]: 0.5 for a in valid_actions}

        if random.random() < self.epsilon:
            return random.choice(valid_actions)
        best_action = max(self.q_table[state], key=self.q_table[state].get)
        return next(a for a in valid_actions if a["action"] == best_action)

    def update(self, state, action, reward, next_state, valid_actions):
        if next_state not in self.q_table:
            self.q_table[next_state] = {a["action"]: 0.5 for a in valid_actions}

        max_q_next = max(self.q_table[next_state].values())
        current_q = self.q_table[state].get(action, 0.5)
        self.q_table[state][action] = current_q + self.alpha * (
            reward + self.gamma * max_q_next - current_q
        )


class AgentPlayer(BasePokerPlayer):
    def __init__(self, input_receiver=None):
        self.input_receiver = (
            input_receiver if input_receiver else self.__gen_raw_input_wrapper()
        )
        self.has_triggered_fold = False
        self.is_bb = False
        self.updated = False
        self.fold_win_threshold = 1150
        self.previous_stack = 1000
        self.opponent_stack = 1000
        self.own_side_pot = False
        self.max_r = 0
        self.Win_rate = self.__init_win_rate__()
        self.policy = RLPolicy()
        self.last_state = None
        self.last_action = None

    def declare_action(self, valid_actions, hole_card, round_state):
        seats = round_state["seats"]
        for i, seat in enumerate(seats):
            if seat["uuid"] == self.uuid:
                self_pos = i
                current_stack = seat["stack"]
                break
            else:
                oppenent_current_stack = seat["stack"]

        community_card = round_state.get("community_card", [])
        raise_act_min = valid_actions[2]["amount"]["min"]
        raise_act_max = valid_actions[2]["amount"]["max"]
        sb_pos = round_state["small_blind_pos"]
        bb_pos = round_state["big_blind_pos"]

        if "small_blind_amount" in round_state:
            sb_value = round_state["small_blind_amount"]
            bb_value = 2 * sb_value
        else:
            sb_value = 10
            bb_value = 20

        if self_pos == sb_pos:
            self.is_bb = False
        elif self_pos == bb_pos:
            self.is_bb = True

        if not self.updated:
            self.updated = True
            if self.is_bb:
                self.fold_win_threshold -= bb_value
            else:
                self.fold_win_threshold -= sb_value

        to_call = valid_actions[1]["amount"]
        EWR = 0.0
        street = round_state.get("street", "")

        if street == "preflop":
            MCS = Starting_Hand_WR(hole_card)
            self.Win_rate["preflop"]["times"] += 1
            self.Win_rate["preflop"]["rate"] = (
                MCS
                + self.Win_rate["preflop"]["rate"]
                * (self.Win_rate["preflop"]["times"] - 1)
            ) / self.Win_rate["preflop"]["times"]
            EWR = self.Win_rate["preflop"]["rate"]

        elif street == "flop" or street == "turn":
            MCS = monte_carlo_win_rate(hole_card, community_card, iterations=20000)
            if street == "flop":
                self.Win_rate["flop"]["times"] += 1
                self.Win_rate["flop"]["rate"] = (
                    MCS
                    + self.Win_rate["flop"]["rate"]
                    * (self.Win_rate["flop"]["times"] - 1)
                ) / self.Win_rate["flop"]["times"]
                EWR = (
                    0.9 * self.Win_rate["flop"]["rate"]
                    + 0.1 * self.Win_rate["preflop"]["rate"]
                )
            else:
                self.Win_rate["turn"]["times"] += 1
                self.Win_rate["turn"]["rate"] = (
                    MCS
                    + self.Win_rate["turn"]["rate"]
                    * (self.Win_rate["turn"]["times"] - 1)
                ) / self.Win_rate["turn"]["times"]
                EWR = (
                    0.95 * self.Win_rate["turn"]["rate"]
                    + 0.05 * self.Win_rate["flop"]["rate"]
                )

        elif street == "river":
            MCS = river_WR_test(hole_card, community_card)
            self.Win_rate["river"]["times"] += 1
            self.Win_rate["river"]["rate"] = (
                MCS
                + self.Win_rate["river"]["rate"] * (self.Win_rate["river"]["times"] - 1)
            ) / self.Win_rate["river"]["times"]
            EWR = (
                0.96 * self.Win_rate["river"]["rate"]
                + 0.04 * self.Win_rate["turn"]["rate"]
            )
        else:
            EWR = 0.5

        try:
            state = f"{street}_{round(float(EWR), 1)}"
        except (TypeError, ValueError):
            state = f"{street}_0.5"

        action = self.policy.get_action(state, valid_actions)
        self.last_state = state
        self.last_action = action["action"]

        amount = action["amount"]
        if action["action"] == "raise" and isinstance(amount, dict):
            to_call = valid_actions[1]["amount"]
            raise_min = amount["min"]
            raise_max = amount["max"]

            # Smarter capped raise instead of all-in
            ideal_raise = to_call * random.uniform(1.5, 2.5)
            capped_raise = min(raise_max, max(raise_min, int(ideal_raise)))
            amount = capped_raise

        return action["action"], amount

    def receive_game_start_message(self, game_info):
        rules = game_info.get("rule", {})
        max_round = rules.get("max_round", "N/A")
        sb_value = rules.get("small_blind_amount", "N/A")
        bb_value = sb_value * 2 if isinstance(sb_value, int) else "N/A"
        init_stack = rules.get("initial_stack", "N/A")
        self.fold_win_threshold = init_stack + (sb_value + bb_value) * (
            (max_round + 1) // 2
        )
        self.max_r = max_round

    def receive_round_start_message(self, round_count, hole_card, seats):
        self.own_side_pot = False
        self.__reset_win_rate()

    def receive_game_update_message(self, new_action, round_state):
        pass

    def receive_street_start_message(self, street, round_state):
        pass

    def receive_round_result_message(self, winners, hand_info, round_state):
        reward = 1 if any(winner["uuid"] == self.uuid for winner in winners) else -1
        street = round_state.get("street", "")
        final_state = f"{street}_end"
        valid_actions = [
            {"action": "fold"},
            {"action": "call"},
            {"action": "raise"},
        ]
        self.policy.update(
            self.last_state, self.last_action, reward, final_state, valid_actions
        )
        self.policy.save_qtable()
        self.updated = False

    def __wait_until_input(self):
        input("Enter some key to continue ...")

    def __gen_raw_input_wrapper(self):
        return lambda msg: input(msg)

    def __reset_win_rate(self):
        self.Win_rate = self.__init_win_rate__()

    def __init_win_rate__(self):
        return {
            "preflop": {"rate": 0.0, "times": 0},
            "flop": {"rate": 0.0, "times": 0},
            "turn": {"rate": 0.0, "times": 0},
            "river": {"rate": 0.0, "times": 0},
        }


def setup_ai():
    return AgentPlayer()

