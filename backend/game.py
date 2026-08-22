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
        self.vote = None 
        self.websocket: Optional[WebSocket] = None
        self.connected = True
        self.removal_task: Optional[asyncio.Task] = None

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "is_host": self.is_host,
            "is_admin": self.is_admin,
            "is_bot": self.is_bot,
            "eliminated": self.eliminated,
            "connected": self.connected,
        }


class Room:
    DISCONNECT_GRACE_SECONDS = 45

    def __init__(self, code: str, mode: str = "single"):
        self.code = code
        self.players: Dict[str, Player] = {}
        self.state = "lobby" 
        self.sub_state = "reveal" 
        
        self.mode = mode 
        self.total_speaking_rounds = 1 
        self.current_cycle_round = 1    
        self.is_tiebreaker = False
        
        self.current_turn_index = 0
        self.timer = 0
        self.timer_task: Optional[asyncio.Task] = None

        self.imposter_ids: List[str] = []
        self.common_word = ""
        self.imposter_word = ""

        self.announcement_text = ""
        self.winner = None
        self.end_msg = ""

    def get_active_players(self) -> List[Player]:
        return [p for p in self.players.values() if not p.eliminated]

    def name_taken(self, name: str, exclude_id: str = None) -> bool:
        target = name.strip().lower()
        return any(
            p.name.strip().lower() == target
            for pid, p in self.players.items()
            if pid != exclude_id
        )

    def add_player(self, name: str, is_host: bool = False, is_bot: bool = False) -> Player:
        player_id = f"bot_{uuid.uuid4().hex[:6]}" if is_bot else uuid.uuid4().hex[:8]
        player = Player(player_id, name, is_host=is_host, is_bot=is_bot)
        self.players[player_id] = player
        return player

    def remove_player(self, player_id: str):
        player = self.players.get(player_id)
        if player and player.removal_task:
            player.removal_task.cancel()
        if player_id in self.players:
            del self.players[player_id]

    def reconnect_player(self, player_id: str, websocket) -> Optional[WebSocket]:
        """Attach a fresh websocket to an existing player. Returns the old
        socket (if any) so the caller can close it, preventing duplicate
        live connections for the same player."""
        player = self.players.get(player_id)
        if not player:
            return None
        if player.removal_task:
            player.removal_task.cancel()
            player.removal_task = None
        old_ws = player.websocket
        player.connected = True
        player.websocket = websocket
        return old_ws

    def mark_disconnected(self, player_id: str):
        """Called when a player's socket drops. Instead of deleting them
        immediately (which would kill their word/vote/imposter state and
        block a quick reconnect), give them a grace window to come back."""
        player = self.players.get(player_id)
        if not player:
            return
        player.connected = False
        player.websocket = None
        if player.removal_task:
            player.removal_task.cancel()
        player.removal_task = asyncio.create_task(self._remove_after_grace(player_id))

    async def _remove_after_grace(self, player_id: str):
        try:
            await asyncio.sleep(self.DISCONNECT_GRACE_SECONDS)
        except asyncio.CancelledError:
            return
        player = self.players.get(player_id)
        if player and not player.connected:
            self.remove_player(player_id)
            await self.broadcast_state()

    async def broadcast_state(self):
        active_players = self.get_active_players()
        current_speaker = active_players[self.current_turn_index] if active_players and self.current_turn_index < len(active_players) else None

        imposter_names = [self.players[imp_id].name for imp_id in self.imposter_ids if imp_id in self.players]

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
                "mode": self.mode,
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
                "announcement_text": self.announcement_text,
                "my_vote": p.vote,
                "my_vote_name": target_voted_name,
                "winner": self.winner,
                "end_msg": self.end_msg,
                "imposter_name": ", ".join(imposter_names) if imposter_names else "Unknown",
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

        for p in self.players.values():
            p.eliminated = False
            p.vote = None

        self.common_word, self.imposter_word = get_random_word_pair()
        player_list = list(self.players.values())
        
        num_imposters = 2 if self.mode == "double" and len(player_list) >= 5 else 1
        imposters = random.sample(player_list, num_imposters)
        self.imposter_ids = [imp.id for imp in imposters]

        for p in player_list:
            p.word = self.imposter_word if p.id in self.imposter_ids else self.common_word

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
        self.start_phase_timer(30, self.next_turn)

    async def finish_turn(self, player_id: str):
        player = self.players.get(player_id)
        if not player or player.eliminated:
            return

        active = self.get_active_players()
        current_speaker = active[self.current_turn_index] if self.current_turn_index < len(active) else None

        if current_speaker and player_id == current_speaker.id:
            await self.next_turn()

    async def next_turn(self):
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
            if p.vote:
                vote_counts[p.vote] = vote_counts.get(p.vote, 0) + 1

        eliminated_id = None
        skip_wins = False
        is_tie = False

        if not vote_counts:
            is_tie = True
        else:
            max_votes = max(vote_counts.values())
            top_voted = [pid for pid, cnt in vote_counts.items() if cnt == max_votes]
            if len(top_voted) == 1:
                winner = top_voted[0]
                if winner == "SKIP":
                    skip_wins = True
                else:
                    eliminated_id = winner
            else:
                is_tie = True

        if is_tie:
            self.is_tiebreaker = True
            self.total_speaking_rounds += 1
            self.announcement_text = f"It's a tie! Round {self.total_speaking_rounds} (Tiebreaker Speaking Round)"
            self.sub_state = "announcement"
            self.start_phase_timer(4, self.start_speaking_round)
            return

        if skip_wins:
            self.is_tiebreaker = False
            self.current_cycle_round = 1
            self.total_speaking_rounds += 1
            self.announcement_text = f"The group voted to skip. No one was eliminated. Starting Round {self.total_speaking_rounds}."
            self.sub_state = "announcement"
            self.start_phase_timer(5, self.start_speaking_round)
            return

        eliminated_player = self.players[eliminated_id]
        eliminated_player.eliminated = True

        active_imposters = [p for p in self.get_active_players() if p.id in self.imposter_ids]
        active_after = self.get_active_players()

        if len(active_imposters) == 0:
            if self.mode == "double":
                self.end_game("crew", "Crewmates won! All Imposters were voted out!")
            else:
                self.end_game("crew", f"Crewmates won! {eliminated_player.name} was the Imposter!")
            return

        if len(active_after) <= 3 and len(active_imposters) >= 1:
            if eliminated_id in self.imposter_ids:
                msg = f"{eliminated_player.name} was an Imposter, but 3 or fewer players remain! Imposters win!"
            else:
                msg = f"{eliminated_player.name} was NOT an Imposter! Imposters win!"
            self.end_game("imposter", msg)
            return

        self.is_tiebreaker = False
        self.current_cycle_round = 1
        self.total_speaking_rounds += 1

        was_imp_text = "an Imposter" if eliminated_id in self.imposter_ids else "NOT an Imposter"
        self.announcement_text = f"{eliminated_player.name} was {was_imp_text}! Starting Round {self.total_speaking_rounds}."
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

    def create_room(self, host_name: str, mode: str = "single") -> tuple[Room, Player]:
        code = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=4))
        room = Room(code, mode)
        host_player = room.add_player(host_name, is_host=True)
        self.rooms[code] = room
        return room, host_player

    def get_room(self, code: str) -> Optional[Room]:
        return self.rooms.get(code.upper())


game_manager = GameManager()
