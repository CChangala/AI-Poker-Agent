class OpponentModel:
    def __init__(self):
        # record frequency
        self.actions = {'fold': 0, 'call': 0, 'raise': 0}

    def update_model(self, action, amount=0):
        if action in self.actions:
            self.actions[action] += 1

    def get_opponent_style(self):
        # judge type
        total_actions = sum(self.actions.values())
        if total_actions == 0:
            return 'unknown'
        aggression_factor = self.actions['raise'] / total_actions
        if aggression_factor < 0.2:
            return 'conservative'
        elif aggression_factor < 0.5:
            return 'balanced'
        else:
            return 'aggressive'
