import functools
import random
import numpy as np
from gymnasium.spaces import Discrete, MultiDiscrete
from pettingzoo import AECEnv
from pettingzoo.utils import agent_selector, wrappers

# Constants for the game
RANKS = ["ACE", "JACK", "QUEEN", "KING"]
NUM_CARDS_PER_RANK = 4  # Each rank has 4 cards
ACTION_PLAY = 0
ACTION_CHALLENGE = 1


def env(num_players=2, render_mode=None):
    """Wrapper for the Bluff environment."""
    internal_render_mode = render_mode if render_mode != "ansi" else "human"
    base_env = BluffEnv(num_players=num_players, render_mode=internal_render_mode)
    if render_mode == "ansi":
        base_env = wrappers.CaptureStdoutWrapper(base_env)
    base_env = wrappers.AssertOutOfBoundsWrapper(base_env)
    base_env = wrappers.OrderEnforcingWrapper(base_env)
    return base_env

class BluffEnv(AECEnv):
    metadata = {"render_modes": ["human"], "name": "bluff_v1"}

    def __init__(self, num_players: int = 2, render_mode=None) -> None:
        """Initialize the Bluff environment with the specified number of players."""
        self.num_players = num_players
        self.render_mode = render_mode
        
        self._first_action_played = False

        self.possible_agents = [f"player_{i}" for i in range(num_players)]
        self.agent_name_mapping = {agent: i for i, agent in enumerate(self.possible_agents)}

        # Define action and observation spaces
        self._action_spaces = {agent: Discrete(2) for agent in self.possible_agents}  # Play or challenge
        self._observation_spaces = {
            agent: MultiDiscrete([len(RANKS), NUM_CARDS_PER_RANK]) for agent in self.possible_agents
        }
        
    @functools.lru_cache(maxsize=None)
    def observation_space(self, agent: str) -> Discrete:
        '''
        Return the observation space for the specified agent.
        '''
        return self._observation_spaces[agent]
    
    @functools.lru_cache(maxsize=None)
    def action_space(self, agent: str) -> Discrete:
        if not self._first_action_played:
            self._first_action_played = True
            return Discrete(1)
            
        return self._action_spaces[agent]
    
    
    
    def reset(self, seed: int=None, options: dict=None) -> None:
        """Reset the environment to start a new game."""
        # super().reset(seed=seed)

        # Deck and hand initialization
        deck = RANKS * NUM_CARDS_PER_RANK
        random.shuffle(deck)
        cards_per_player = len(deck) // self.num_players

        # Assign cards to players and discard extras
        self.player_hands = {
            agent: deck[i * cards_per_player:(i + 1) * cards_per_player]
            for i, agent in enumerate(self.possible_agents)
        }
        self.central_pile = deck[self.num_players * cards_per_player:]
        
        self._first_action_played = False

        # Game state variables
        self.current_rank = 0  # Start with "ACE"
        self.current_claim = []  # Cards claimed to be played
        self.last_played_agent = None
        self.current_player_index = 0

        self.agents = self.possible_agents[:]
        self.rewards = {agent: 0 for agent in self.agents}
        self.terminations = {agent: False for agent in self.agents}
        self.truncations = {agent: False for agent in self.agents}
        self.infos = {agent: {} for agent in self.agents}

        self._agent_selector = agent_selector(self.agents)
        self.agent_selection = self._agent_selector.next()
        
                
    def observe(self, agent: str) -> dict:
        """Return the current observation for the specified agent."""
        return {
            "current_rank": self.current_rank,
            "central_pile_size": len(self.central_pile),
            "hand": self.player_hands[agent],
        }
        
    def step(self, action: str) -> None:
        """Take a step in the game."""
        agent = self.agent_selection

        if action not in [ACTION_PLAY, ACTION_CHALLENGE]:
            raise ValueError(f"Invalid action: {action}")

        if action == ACTION_PLAY:
            # Agent plays cards face down
            print('here')
            self._handle_play(agent)

        elif action == ACTION_CHALLENGE:
            # Agent challenges the last play
            self._handle_challenge(agent)
            
        if self.render_mode == "human":
            print("\n--- Current Game State ---")
            print('Action:', action)
            self.render()

        # Move to the next player
        if not self.terminations[agent]:
            self.agent_selection = self._agent_selector.next()

        
            
    def _handle_play(self, agent: str) -> None:
        """Handle the play action."""

        # Randomly select cards from the player's hand (game assumes legal play for now). Fix later
        hand = self.player_hands[agent]
        # cards_to_play = [card for card in hand if card == RANKS[self.current_rank]]
        cards_to_play = random.sample(hand, 1)

        if not cards_to_play:
            raise ValueError("Agent must play at least one card.")

        # Add cards to the central pile
        self.central_pile.extend(cards_to_play)
        self.current_claim = cards_to_play
        self.last_played_agent = agent

        # Remove played cards from the agent's hand
        self.player_hands[agent] = [card for card in hand if card not in cards_to_play]

        # Check for victory
        self._check_victory(agent)
    
    def _check_victory(self, agent: str) -> None:
        if not self.player_hands[agent]:
            self.terminations[agent] = True
            self.rewards[agent] = 1
            for other_agent in self.agents:
                if other_agent != agent:
                    self.terminations[other_agent] = True
                    self.rewards[other_agent] = -1
                    
    def _handle_challenge(self, agent):
        """Handle the challenge action."""
        if self.last_played_agent is None:
            raise RuntimeError("No play to challenge.")

        # Check if the last play was truthful
        is_truthful = all(card == RANKS[self.current_rank] for card in self.current_claim)

        if is_truthful:
            # Challenger takes all cards in the central pile
            self.player_hands[agent].extend(self.central_pile)
        else:
            # Last player takes all cards in the central pile
            self.player_hands[self.last_played_agent].extend(self.central_pile)

        # Reset the central pile and move to the next rank
        self.central_pile = []
        self.current_rank = (self.current_rank + 1) % len(RANKS)
        
    def render(self):
        """Render the current game state."""
        print(f"Current turn: {self.agent_selection}")
        print(f"Current observation for {self.agent_selection}: {self.observe(self.agent_selection)}")
        print(f"Central pile: {len(self.central_pile)} cards")
        print(f"Current rank: {RANKS[self.current_rank]}")
        for agent in self.agents:
            print(f"{agent}: {len(self.player_hands[agent])} cards")
        
            

    def close(self):
        """Clean up the environment."""
        pass