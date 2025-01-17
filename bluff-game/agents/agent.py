class Agent:
    def __init__(self, name, strategy):
        self.name = name
        self.hand = []
        self.strategy = strategy
        
    def play_cards(self):
        pass

    def challenge(self,):
        """
        Decide whether to challenge the claim.
        """
        pass

    def receive_cards(self, cards):
        """
        Add cards to the agent's hand.
        """
        self.hand.extend(cards)

    def __str__(self):
        return f"{self.name} (Hand: {len(self.hand)} cards)"
