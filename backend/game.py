import random
import string
from typing import Dict, Any
from fastapi import WebSocket
from backend.words import WORD_PAIRS

class GameManager:
    def __init__(self):
        self.games: Dict[str, Dict[str, Any]] = {}
        self.connections: Dict[str, Dict[str, WebSocket]] = {}

    def room_exists(self, game_code: str) -> bool:
        return game_code in self.games

    def create_room(self, host_id: str, host_name: str) -> str:
        while True:
            game_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
            if game_code not in self.games:
                break

        self.games[game_code] = {
            "host": host_id,
            "players": {
                host_id: {"name": host_name, "word": None, "is_imposter": False, "eliminated": False}
            },
            "state": "lobby"
        }
        self.connections[game_code] = {}
        return game_code

    def add_player(self, game_code: str, player_id: str, player_name: str) -> bool:
        if game_code not in self.games:
            return False
        if self.games[game_code]["state"] != "lobby":
            return False  # Can't join mid-game
        
        self.games[game_code]["players"][player_id] = {
            "name": player_name,
            "word": None,
            "is_imposter": False,
            "eliminated": False
        }
        return True

    def start_game(self, game_code: str):
        game = self.games[game_code]
        players = game["players"]
        
        if len(players) < 3:
            return False # Need at least 3 players

        # Pick random word pair
        pair = random.choice(WORD_PAIRS)
        common_word = pair["word1"]
        imposter_word = pair["word2"]

        # Pick random imposter
        player_ids = list(players.keys())
        imposter_id = random.choice(player_ids)

        for pid, pdata in players.items():
            if pid == imposter_id:
                pdata["is_imposter"] = True
                pdata["word"] = imposter_word
            else:
                pdata["is_imposter"] = False
                pdata["word"] = common_word
            pdata["eliminated"] = False

        game["state"] = "playing"
        return True

    async def connect(self, game_code: str, player_id: str, websocket: WebSocket):
        await websocket.accept()
        if game_code not in self.connections:
            self.connections[game_code] = {}
        self.connections[game_code][player_id] = websocket
        await self.broadcast_room_state(game_code)

    def disconnect(self, game_code: str, player_id: str):
        if game_code in self.connections and player_id in self.connections[game_code]:
            del self.connections[game_code][player_id]
        
        if game_code in self.games and player_id in self.games[game_code]["players"]:
            # If host leaves, remove room or transfer host
            del self.games[game_code]["players"][player_id]
            if not self.games[game_code]["players"]:
                del self.games[game_code]

    async def broadcast_room_state(self, game_code: str):
        if game_code not in self.games:
            return
        
        game = self.games[game_code]
        conn_dict = self.connections.get(game_code, {})

        for pid, ws in conn_dict.items():
            player_info = game["players"].get(pid, {})
            state_data = {
                "type": "room_state",
                "game_code": game_code,
                "is_host": (game["host"] == pid),
                "state": game["state"],
                "players": [{ "id": p_id, "name": p_val["name"], "eliminated": p_val["eliminated"] } for p_id, p_val in game["players"].items()],
                "my_word": player_info.get("word", "")
            }
            await ws.send_json(state_data)

    async def handle_action(self, game_code: str, player_id: str, data: dict):
        action = data.get("action")
        game = self.games.get(game_code)
        if not game:
            return

        if action == "start_game" and game["host"] == player_id:
            success = self.start_game(game_code)
            if success:
                await self.broadcast_room_state(game_code)

game_manager = GameManager()