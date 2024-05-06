from pypokerengine.players import BasePokerPlayer
import random
import math


class MCTSNode:
    def __init__(self, state, parent=None, action=None):
        self.state = state
        self.parent = parent
        self.children = []
        self.visits = 0
        self.value = 0
        self.untried_actions = state.valid_actions.copy()
        self.action = action

    def select_child(self, c_param= 2.0):
        log_n = math.log(self.visits)
        best_score = -float('inf')
        best_child = None
        for child in self.children:
            exploit = child.value / child.visits
            explore = c_param * math.sqrt(log_n / child.visits)
            score = exploit + explore
            if score > best_score:
                best_score = score
                best_child = child
        return best_child

    def expand(self):
        action = self.untried_actions.pop()
        state = self.state.apply_action(action)
        child = MCTSNode(state, self, action)
        self.children.append(child)
        return child

    def backpropagate(self, result):
        self.visits += 1
        self.value += result if result >= 0 else result * 0.5
        if self.parent:
            self.parent.backpropagate(-result)

class MCTSPlayer(BasePokerPlayer):
    def __init__(self):
        self.hole_card = None
        self.game_state = None
        self.stack = 0

    def declare_action(self, valid_actions, hole_card, round_state):
        self.hole_card = hole_card
        self.game_state = round_state
        root = MCTSNode(round_state)
        for _ in range(200):
            node = root
            state = round_state.copy()

            while node.untried_actions == [] and node.children != []:
                node = node.select_child()
                state.apply_action(node.action)

            if node.untried_actions != []:
                node = node.expand()
                state = node.state

            result = self.simulate(state)
            node.backpropagate(result)

        best_child = max(root.children, key=lambda c: c.visits)
        return best_child.action

    def simulate(self, state):
        while not state.is_terminal():
            action = random.choice(state.valid_actions)
            state = state.apply_action(action)
        return state.winners[0].stack - sum(p.stack for p in state.players if p != state.winners[0])

    def receive_game_start_message(self, game_info):
        self.stack = game_info["player_stack"]

    def receive_round_start_message(self, round_count, hole_card, seats):
        self.hole_card = hole_card

    def receive_street_start_message(self, street, round_state):
        self.game_state = round_state

    def receive_game_update_message(self, action, round_state):
        self.game_state = round_state

    def receive_round_result_message(self, winners, hand_info, round_state):
        player = round_state.seats.players[0]  # Assuming we are always player 0
        self.stack = player.stack

        # If we're not the winner and our stack is low, go all-in
        if player not in winners and self.stack < 100:
            self.game_state.valid_actions = [self.game_state.valid_actions[-1]]

def setup_ai():
    return MCTSPlayer()