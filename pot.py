from typing import Dict, List, Set

from player import Player
from poker import best_possible_hand, Card, Hand

# A class for representing one pot or side pot
class Pot:
    def __init__(self, players: Set[Player]) -> None:
        # The players that have contributed to this pot and can win it
        self.players = players
        # The bet that needs to be made to join this pot (in addition to the
        # bets of the lower pots)
        self.cur_bet = 0
        # The amount of money accumulated in this pot
        self.amount = 0
        if len(players) > 0:
            # The maximum bet that can be held by this pot before it
            # needs a side pot
            self.max_bet = min(player.max_bet for player in players)
        else:
            # It might be possible to raise the bet beyond what any players can
            # pay if the blinds raise high enough. If so, this pot should never
            # be reached by any players, so we set the max bet extremely high
            # to hopefully prevent accidental creation of another side pot
            self.max_bet = 10000000000000000000000000000

    # Returns which players win this pot, based on the given community cards
    def get_winners(self, shared_cards: List[Card]) -> List[Player]:
        winners: List[Player] = []
        best_hand: Hand = None
        for player in self.players:
            hand = best_possible_hand(shared_cards, player.cards)
            if best_hand is None or hand > best_hand:
                winners = [player]
                best_hand = hand
            elif hand == best_hand:
                winners.append(player)
        return winners

    # Returns a new side pot, for when the bet overflows what can be contained
    # in this pot
    def make_side_pot(self):
        excluded = {player for player in self.players
                    if player.max_bet == self.max_bet}
        return Pot(self.players - excluded)

# A class to manage pots and side pots and who is in each pot and how much
# each player has bet so far
class PotManager:
    def __init__(self):
        # List of side pots in the game
        # If nobody's all-in, there should only be one pot
        # Higher-priced pots are towards the end of the list
        self.pots: List[Pot] = []

    # Resets the list of pots for a new hand
    def new_hand(self, players: List[Player]) -> None:
        self.pots = [Pot(set(players))]

    # Returns the current bet to be matched
    @property
    def cur_bet(self) -> int:
        return sum(pot.cur_bet for pot in self.pots)

    # Returns the amount of money that's in all the pots and side pots
    @property
    def value(self) -> int:
        return sum(pot.amount for pot in self.pots)

    # Increases the current bet to a new given amount
    def increase_bet(self, new_amount: int) -> None:
        accumulated_bet = 0
        while self.pots[-1].max_bet < new_amount:
            self.pots[-1].cur_bet = self.pots[-1].max_bet - accumulated_bet
            accumulated_bet += self.pots[-1].cur_bet
            self.pots.append(self.pots[-1].make_side_pot())
        new_bet = min(self.pots[-1].max_bet, new_amount)
        self.pots[-1].cur_bet = new_bet - accumulated_bet

    # Returns all the players that are in the pot
    def in_pot(self) -> Set[Player]:
        return self.pots[0].players

    def debug_print(self):
        for i, pot in enumerate(self.pots):
            print(f"Pot #{i}. Bet: ${pot.cur_bet} (Max: {pot.max_bet}). "
                  f"Amount: ${pot.amount}.")
            for player in pot.players:
                print(f"{player.name}: {player.balance}")
            print("-----")

    # Handles a player folding, removing them from every pot that they're
    # eligible for
    def handle_fold(self, player: Player) -> None:
        for pot in self.pots:
            if player in pot.players:
                pot.players.remove(player)

    # Handles a player calling the current bet
    def handle_call(self, player: Player) -> None:
        new_amount = player.bet(min(player.max_bet, self.cur_bet))
        old_bet = player.cur_bet - new_amount
        pot_index = 0
        while new_amount > 0:
            cur_pot = self.pots[pot_index]
            old_bet -= cur_pot.cur_bet
            if old_bet < 0:
                cur_pot.amount -= old_bet
                new_amount += old_bet
                old_bet = 0
            pot_index += 1
        player.placed_bet = True

    # Handles a player raising the current bet to a given amount
    def handle_raise(self, player: Player, new_amount: int) -> None:
        self.increase_bet(self.cur_bet + new_amount)
        self.handle_call(player)

    # Pays the initial blinds for the player, returning whether they were
    # forced to go all-in by the blind
    def pay_blind(self, player: Player, blind: int) -> bool:
        self.increase_bet(blind)
        self.handle_call(player)
        player.placed_bet = False
        return player.balance == 0

    # Returns whether the betting round is over, which is where every player
    # who can bet has made a bet and have matched the same bet
    def round_over(self) -> bool:
        if self.betting_over():
            return True
        for player in self.pots[0].players:
            if player.balance == 0:
                continue
            elif not player.placed_bet or player.cur_bet < self.cur_bet:
                return False
        return True

    # Returns whether all betting is over, if all but one player has folded or
    # has gone all-in
    def betting_over(self) -> bool:
        players_left_betting = False
        for player in self.pots[0].players:
            if player.balance > 0:
                if players_left_betting or not player.placed_bet:
                    return False
                if player.cur_bet < self.cur_bet:
                    return False
                players_left_betting = True
        return True

    # Returns the winners of the pot, and the amounts that they won
    def get_winners(self, shared_cards: List[Card]) -> Dict[Player, int]:
        winners: Dict[Player, int] = {}
        for pot in self.pots:
            pot_winners = pot.get_winners(shared_cards)
            if len(pot_winners) == 0:
                continue
            pot_won = pot.amount // len(pot_winners)
            if pot_won > 0:
                for winner in pot_winners:
                    winners.setdefault(winner, 0)
                    winners[winner] += pot_won
        return winners

    # Advances to the next round of betting
    def next_round(self) -> None:
        for pot in self.pots:
            pot.cur_bet = 0
            pot.max_bet = 0
        for player in self.pots[-1].players:
            player.placed_bet = False
            player.cur_bet = 0
        self.pots[-1].max_bet = min(player.max_bet
                                    for player in self.pots[-1].players)
