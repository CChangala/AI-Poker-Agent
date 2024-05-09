
from pypokerengine.players import BasePokerPlayer
import random
import math
from pypokerengine.utils.card_utils import estimate_hole_card_win_rate, gen_cards
from opponent_model import OpponentModel

class MCTSPokerPlayer(BasePokerPlayer):
    def __init__(self, num_simulations=100):
        super().__init__()
        self.tree = {}
        self.exploration_constant = 1.9  # UCB1 exploration constant
        self.num_simulations = num_simulations  # Control the number of simulations
        self.opponent_model = OpponentModel()

    def declare_action(self, valid_actions, hole_card, round_state):
        action = self.mcts(valid_actions, hole_card, round_state)
        return action
    
    def receive_game_start_message(self, game_info):
        self.num_players = game_info['player_num']

    def receive_round_start_message(self, round_count, hole_card, seats):
        self.hole_card = hole_card

    def receive_street_start_message(self, street, round_state):
        self.street = street

    def receive_game_update_message(self, new_action, round_state):
        if new_action['player_uuid'] != self.uuid:
            self.opponent_model.update_model(new_action['action'])

    def receive_round_result_message(self, winners, hand_info, round_state):
        pass

    def mcts(self, valid_actions, hole_card, round_state):
        root_state = (tuple(hole_card), tuple(round_state['community_card']), round_state['pot']['main']['amount'])
        if root_state not in self.tree:
            self.tree[root_state] = {action['action']: {'wins': 0, 'visits': 0, 'total_pot': 0} for action in valid_actions}

        total_visits = sum(self.tree[root_state][action]['visits'] for action in self.tree[root_state])
        if total_visits < 10:
            return random.choice(valid_actions)['action']

        for _ in range(self.num_simulations):
            selected_action = self.select_action(root_state, valid_actions)
            win, pot_amount = self.simulate_action(selected_action, hole_card, round_state)
            self.backpropagate(root_state, selected_action, win, pot_amount)

        best_action = max(valid_actions, key=lambda a: self.ucb1(total_visits, root_state, a['action']))
        return best_action['action']

    def select_action(self, state, valid_actions):
        total_visits = sum(self.tree[state][action]['visits'] for action in self.tree[state])
        return max(valid_actions, key=lambda a: self.ucb1(total_visits, state, a['action']))['action']

    def simulate_action(self, selected_action, hole_card, round_state):
        hole_card_gen = gen_cards(hole_card)
        community_card_gen = gen_cards(round_state['community_card'])
        win_rate = estimate_hole_card_win_rate(nb_simulation=1000, nb_player=self.num_players, hole_card=hole_card_gen, community_card=community_card_gen)
        is_win = win_rate > 0.5
        return is_win, round_state['pot']['main']['amount'] * (win_rate - 0.5)  # Simplified model of winnings

    def backpropagate(self, state, action, win, pot_amount):
        node = self.tree[state][action]
        node['visits'] += 1
    
        opponent_style = self.opponent_model.get_opponent_style()
        if opponent_style == 'aggressive':
            value = 1.2 * (1 if win else 0)
        elif opponent_style == 'conservative':
            value = 0.8 * (1 if win else 0)
        else:
            value = 1 if win else 0
    
        node['wins'] += value
        node['total_pot'] += pot_amount if win else 0

    def ucb1(self, total_visits, state, action):
        node = self.tree[state][action]
        mean_win = node['wins'] / node['visits'] if node['visits'] else 0
        total_pot = node['total_pot'] / node['visits'] if node['visits'] else 0
        return mean_win + self.exploration_constant * math.sqrt(math.log(total_visits) / node['visits']) + total_pot


player = MCTSPokerPlayer(num_simulations=1000)