import random
import game.visualize_utils as U
from game.players import BasePokerPlayer
from agents.MCS import Starting_Hand_WR, river_WR_test, monte_carlo_win_rate
from game.engine.card import Card


class ConsolePlayer(BasePokerPlayer):
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

    def declare_action(self, valid_actions, hole_card, round_state):
        print(
            U.visualize_declare_action(valid_actions, hole_card, round_state, self.uuid)
        )
        print(1)
        seats = round_state["seats"]
        for i, seat in enumerate(seats):
            if seat["uuid"] == self.uuid:
                self_pos = i
                current_stack = seat["stack"]
                break
            else:
                oppenent_current_stack = seat["stack"]
        community_card = round_state.get("community_card", [])
        actions = valid_actions
        raise_act_min = actions[2]["amount"]["min"]
        raise_act_max = actions[2]["amount"]["max"]
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
        print(f"\nFold win threshold: {self.fold_win_threshold}")
        print(f"Current stack: {current_stack}")
        print(f"Opponent's stack: {oppenent_current_stack}\n")
        if not self.has_triggered_fold and current_stack > self.fold_win_threshold:
            print(
                f"before fold: {self.has_triggered_fold} at current stack {current_stack}"
            )
            self.has_triggered_fold = True
            print(f"Triggered fold: {self.has_triggered_fold}")

        if self.has_triggered_fold:
            print(f"keep folding")
            return valid_actions[0]["action"], valid_actions[0]["amount"]

        to_call = valid_actions[1]["amount"]
        potential_future_OS = 2000 - current_stack
        EWR = 0.0

        street = round_state.get("street", "")
        if street == "preflop":
            print(f"preflop street")
            MCS = Starting_Hand_WR(hole_card)
            print(f"preflop MCS: {MCS}")
            self.Win_rate["preflop"]["times"] += 1
            self.Win_rate["preflop"]["rate"] = (
                MCS
                + self.Win_rate["preflop"]["rate"]
                * (self.Win_rate["preflop"]["times"] - 1)
            ) / self.Win_rate["preflop"]["times"]
            EWR = self.Win_rate["preflop"]["rate"]

        elif street == "flop" or street == "turn":
            MCS = monte_carlo_win_rate(hole_card, community_card, iterations=20000)
            print(f"preflop MCS: {MCS}")
            if street == "flop":
                print(f"flop street")
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
                print(f"flop EWR: {EWR}")
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
                print(f"turn EWR: {EWR}")

        elif street == "river":
            print(f"river street")
            MCS = river_WR_test(hole_card, community_card)
            print(f"river MCS: {MCS}")
            self.Win_rate["river"]["times"] += 1
            self.Win_rate["river"]["rate"] = (
                MCS
                + self.Win_rate["river"]["rate"] * (self.Win_rate["river"]["times"] - 1)
            ) / self.Win_rate["river"]["times"]
            EWR = (
                0.96 * self.Win_rate["river"]["rate"]
                + 0.04 * self.Win_rate["turn"]["rate"]
            )
            print(f"river EWR: {EWR}")
        else:
            EWR = 0.5

        if EWR < 0.3 and street != "preflop":
            print(f"low EWR: {EWR}, folding")
            return valid_actions[0]["action"], valid_actions[0]["amount"]

        elif EWR >= 0.8:
            print(f"high EWR: {EWR}, raising max")
            return valid_actions[2]["action"], raise_act_max

        elif EWR >= 0.5:
            if to_call <= 100:
                print(f"moderate EWR: {EWR}, calling {to_call}")
                return valid_actions[1]["action"], to_call
            else:
                print(f"moderate EWR: {EWR}, raising min {raise_act_min}")
                return valid_actions[2]["action"], raise_act_min
        else:
            print(f"low EWR: {EWR}, calling {to_call}")
            return valid_actions[1]["action"], to_call

    def receive_game_start_message(self, game_info):
        print(U.visualize_game_start(game_info, self.uuid))
        rules = game_info.get("rule", {})
        max_round = rules.get("max_round", "N/A")
        sb_value = rules.get("small_blind_amount", "N/A")
        bb_value = sb_value * 2 if isinstance(sb_value, int) else "N/A"
        init_stack = rules.get("initial_stack", "N/A")

        self.fold_win_threshold = init_stack + (sb_value * 3) * (int)(
            (max_round + 1) // 2
        )
        self.max_r = max_round
        self.__wait_until_input()

    def receive_round_start_message(self, round_count, hole_card, seats):
        print(U.visualize_round_start(round_count, hole_card, seats, self.uuid))
        self.__wait_until_input()
        self.own_side_pot = False
        self.__reset_win_rate()

    def receive_street_start_message(self, street, round_state):
        print(U.visualize_street_start(street, round_state, self.uuid))
        self.__wait_until_input()

    def receive_game_update_message(self, new_action, round_state):
        print(U.visualize_game_update(new_action, round_state, self.uuid))
        self.__wait_until_input()

    def receive_round_result_message(self, winners, hand_info, round_state):
        print(U.visualize_round_result(winners, hand_info, round_state, self.uuid))
        self.updated = False
        self.__wait_until_input()

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
    return ConsolePlayer()

