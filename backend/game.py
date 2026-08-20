import asyncio
import random
import uuid
from typing import Dict, List, Optional
from fastapi import WebSocket

try:
    from backend.words import get_random_word_pair
except ImportError:
    from words import get_random_word_pair


class Player:
    def __init__(self, player_id: str, name: str, is_host: bool = False, is_bot: bool = False):
        self.id = player_id
        self.name = name
        self.is_host = is_host
        self.is_admin = False
        self.is_bot = is_bot
        self.eliminated = False
        self.word = ""
        self.vote = None  # None, target_id, or "SKIP"
        self.websocket: Optional[WebSocket] = None

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "is_host": self.is_host,
            "is_admin": self.is_admin,
            "is_bot": self.is_bot,
            "eliminated": self.eliminated,
        }


class Room:
    def __init__(self, code: str):
        self.code = code
        self.players: Dict[str, Player] = {}
        self.state = "lobby"  # lobby, playing, game_over
        self.sub_state = "reveal"  # reveal, speaking, announcement, voting
        
        self.total_speaking_rounds = 1  # 1, 2, 3, 4...
        self.current_cycle_round = 1    # 1 or 2
        self.is_tiebreaker = False
        
        self.current_turn_index = 0
        self.timer = 0
        self.timer_task: Optional[asyncio.Task] = None

        self.imposter_id: Optional[str] = None
        self.common_word = ""
        self.imposter_word = ""

        self.skip_turn_votes = set()
        self.announcement_text = ""
        self.winner = None
        self.end_msg = ""

    def get_active_players(self) -> List[Player]:
        return [p for p in self.players.values() if not p.eliminated]

    def add_player(self, name: str, is_host: bool = False, is_bot: bool = False) -> Player:
        player_id = f"bot_{uuid.uuid4().hex[:6]}" if is_bot else uuid.uuid4().hex[:8]
        player = Player(player_id, name, is_host=is_host, is_bot=is_bot)
        self.players[player_id] = player
        return player

    def remove_player(self, player_id: str):
        if player_id in self.players:
            del self.players[player_id]

    async def broadcast_state(self):
        active_players = self.get_active_players()
        current_speaker = active_players[self.current_turn_index] if active_players and self.current_turn_index < len(active_players) else None

        for p in list(self.players.values()):
            if p.is_bot or not p.websocket:
                continue

            target_voted_name = None
            if p.vote and p.vote != "SKIP":
                target = self.players.get(p.vote)
                target_voted_name = target.name if target else None

            payload = {
                "type": "room_state",
                "game_code": self.code,
                "state": self.state,
                "sub_state": self.sub_state,
                "is_host": p.is_host,
                "timer": self.timer,
                "players": [pl.to_dict() for pl in self.players.values()],
                "my_word": p.word,
                "current_round": self.total_speaking_rounds,
                "current_cycle_round": self.current_cycle_round,
                "is_tiebreaker": self.is_tiebreaker,
                "is_eliminated": p.eliminated,
                "current_turn_id": current_speaker.id if current_speaker else None,
                "current_turn_name": current_speaker.name if current_speaker else "",
                "skip_votes": len(self.skip_turn_votes),
                "skip_votes_needed": (len(active_players) // 2) + 1,
                "announcement_text": self.announcement_text,
                "my_vote": p.vote,
                "my_vote_name": target_voted_name,
                "winner": self.winner,
                "end_msg": self.end_msg,
                "imposter_name": self.players[self.imposter_id].name if self.imposter_id in self.players else "Unknown",
                "common_word": self.common_word,
                "imposter_word": self.imposter_word,
            }

            try:
                await p.websocket.send_json(payload)
            except Exception:
                pass

    def start_game(self):
        self.state = "playing"
        self.sub_state = "reveal"
        self.total_speaking_rounds = 1
        self.current_cycle_round = 1
        self.is_tiebreaker = False
        self.winner = None
        self.end_msg = ""
        self.skip_turn_votes.clear()

        for p in self.players.values():
            p.eliminated = False
            p.vote = None

        self.common_word, self.imposter_word = get_random_word_pair()
        player_list = list(self.players.values())
        imposter = random.choice(player_list)
        self.imposter_id = imposter.id

        for p in player_list:
            p.word = self.imposter_word if p.id == self.imposter_id else self.common_word

        self.start_phase_timer(10, self.start_speaking_round)

    def start_phase_timer(self, seconds: int, callback):
        if self.timer_task:
            self.timer_task.cancel()

        self.timer = seconds
        self.timer_task = asyncio.create_task(self._run_timer(callback))

    async def _run_timer(self, callback):
        while self.timer > 0:
            await self.broadcast_state()
            await asyncio.sleep(1)
            self.timer -= 1
        await self.broadcast_state()
        await callback()

    async def start_speaking_round(self):
        self.sub_state = "speaking"
        self.current_turn_index = 0
        self.skip_turn_votes.clear()
        self.start_phase_timer(30, self.next_turn)

    async def finish_turn(self, player_id: str):
        player = self.players.get(player_id)
        if not player or player.eliminated:
            return

        active = self.get_active_players()
        current_speaker = active[self.current_turn_index] if self.current_turn_index < len(active) else None

        if current_speaker and player_id == current_speaker.id:
            await self.next_turn()
        else:
            self.skip_turn_votes.add(player_id)
            needed = (len(active) // 2) + 1
            if len(self.skip_turn_votes) >= needed:
                await self.next_turn()
            else:
                await self.broadcast_state()

    async def next_turn(self):
        self.skip_turn_votes.clear()
        active = self.get_active_players()
        self.current_turn_index += 1

        if self.current_turn_index >= len(active):
            if self.is_tiebreaker:
                await self.start_voting_phase()
            elif self.current_cycle_round < 2:
                self.current_cycle_round += 1
                self.total_speaking_rounds += 1
                self.announcement_text = f"Round {self.total_speaking_rounds} Speaking Phase"
                self.sub_state = "announcement"
                self.start_phase_timer(3, self.start_speaking_round)
            else:
                await self.start_voting_phase()
        else:
            self.start_phase_timer(30, self.next_turn)

    async def start_voting_phase(self):
        self.sub_state = "voting"
        for p in self.players.values():
            p.vote = None

        self.bot_auto_vote()
        self.start_phase_timer(30, self.evaluate_votes)

    def bot_auto_vote(self):
        active = self.get_active_players()
        for p in active:
            if p.is_bot:
                targets = [other.id for other in active if other.id != p.id]
                targets.append("SKIP")
                p.vote = random.choice(targets)

    async def record_vote(self, voter_id: str, target_id: str):
        voter = self.players.get(voter_id)
        if not voter or voter.eliminated or self.sub_state != "voting":
            return

        voter.vote = target_id
        await self.broadcast_state()

        active = self.get_active_players()
        if all(p.vote is not None for p in active):
            await self.evaluate_votes()

    async def evaluate_votes(self):
        active = self.get_active_players()
        vote_counts = {}

        for p in active:
            if p.vote and p.vote != "SKIP":
                vote_counts[p.vote] = vote_counts.get(p.vote, 0) + 1

        eliminated_id = None
        is_tie = False

        if not vote_counts:
            is_tie = True
        else:
            max_votes = max(vote_counts.values())
            top_voted = [pid for pid, cnt in vote_counts.items() if cnt == max_votes]
            if len(top_voted) == 1:
                eliminated_id = top_voted[0]
            else:
                is_tie = True

        if is_tie:
            self.is_tiebreaker = True
            self.total_speaking_rounds += 1
            self.announcement_text = f"It's a tie! Round {self.total_speaking_rounds} (Tiebreaker Speaking Round)"
            self.sub_state = "announcement"
            self.start_phase_timer(4, self.start_speaking_round)
            return

        eliminated_player = self.players[eliminated_id]
        eliminated_player.eliminated = True

        if eliminated_id == self.imposter_id:
            self.end_game("crew", f"Crewmates won! {eliminated_player.name} was the Imposter!")
            return

        active_after = self.get_active_players()
        if len(active_after) <= 3:
            self.end_game("imposter", f"{eliminated_player.name} was NOT the Imposter! Imposter wins!")
            return

        self.is_tiebreaker = False
        self.current_cycle_round = 1
        self.total_speaking_rounds += 1
        self.announcement_text = f"{eliminated_player.name} was NOT the Imposter! Starting Round {self.total_speaking_rounds}."
        self.sub_state = "announcement"
        self.start_phase_timer(5, self.start_speaking_round)

    def end_game(self, winner: str, end_msg: str):
        self.state = "game_over"
        self.winner = winner
        self.end_msg = end_msg
        if self.timer_task:
            self.timer_task.cancel()
        asyncio.create_task(self.broadcast_state())

    def reset_to_lobby(self):
        self.state = "lobby"
        self.sub_state = "reveal"
        self.is_tiebreaker = False
        self.total_speaking_rounds = 1
        self.current_cycle_round = 1
        if self.timer_task:
            self.timer_task.cancel()
        for p in self.players.values():
            p.eliminated = False
            p.vote = None
        asyncio.create_task(self.broadcast_state())


class GameManager:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}

    def create_room(self, host_name: str) -> tuple[Room, Player]:
        code = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=4))
        room = Room(code)
        host_player = room.add_player(host_name, is_host=True)
        self.rooms[code] = room
        return room, host_player

    def get_room(self, code: str) -> Optional[Room]:
        return self.rooms.get(code.upper())


game_manager = GameManager()
