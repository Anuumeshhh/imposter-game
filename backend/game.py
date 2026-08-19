import random
import string
import asyncio
from typing import Dict, Any
from fastapi import WebSocket
from backend.words import WORD_PAIRS

class GameManager:
    def __init__(self):
        self.games: Dict[str, Dict[str, Any]] = {}
        self.connections: Dict[str, Dict[str, WebSocket]] = {}
        self.tasks: Dict[str, asyncio.Task] = {}

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
            "state": "lobby",
            "sub_state": "none",
            "messages": [],
            "turn_index": 0,
            "turn_order": [],
            "timer": 0,
            "votes": {}
        }
        self.connections[game_code] = {}
        return game_code

    def add_player(self, game_code: str, player_id: str, player_name: str) -> bool:
        if game_code not in self.games:
            return False
        game = self.games[game_code]
        if game["state"] != "lobby":
            return False  # Prevent joining active games
        
        # Prevent duplicate identical user entries
        if player_id in game["players"]:
            return False

        game["players"][player_id] = {
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
            return False

        pair = random.choice(WORD_PAIRS)
        common_word = pair["word1"]
        imposter_word = pair["word2"]

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
        game["sub_state"] = "reveal"
        game["messages"] = []
        
        if game_code in self.tasks:
            self.tasks[game_code].cancel()
        
        # Start game loop background task
        self.tasks[game_code] = asyncio.create_task(self.run_game_loop(game_code))
        return True

    async def run_game_loop(self, game_code: str):
        try:
            # Phase 1: Reveal Word (5 seconds)
            game = self.games[game_code]
            game["timer"] = 5
            await self.broadcast_room_state(game_code)
            
            for _ in range(5):
                await asyncio.sleep(1)
                if game_code not in self.games: return
                game["timer"] -= 1
                await self.broadcast_room_state(game_code)

            # Phase 2: Discussion / Turn-based hints
            game["sub_state"] = "discussion"
            active_players = [pid for pid, p in game["players"].items() if not p["eliminated"]]
            random.shuffle(active_players)
            game["turn_order"] = active_players
            game["turn_index"] = 0

            while game["sub_state"] == "discussion":
                if not game["turn_order"]:
                    break
                current_pid = game["turn_order"][game["turn_index"]]
                game["timer"] = 20  # 20 seconds per person's hint turn
                await self.broadcast_room_state(game_code)

                for _ in range(20):
                    await asyncio.sleep(1)
                    if game_code not in self.games: return
                    game["timer"] -= 1
                    await self.broadcast_room_state(game_code)
                    # Break early if user posted a hint
                    if game["sub_state"] != "discussion":
                        break
                
                if game["sub_state"] == "discussion":
                    # Move to next turn automatically if time runs out
                    game["turn_index"] = (game["turn_index"] + 1) % len(game["turn_order"])
                    if game["turn_index"] == 0:
                        # Completed a full round of hints -> move to voting phase
                        game["sub_state"] = "voting"
                        game["timer"] = 15
                        game["votes"] = {}
                        await self.broadcast_room_state(game_code)
                        break

            # Phase 3: Voting Phase Loop
            while game["sub_state"] == "voting":
                await asyncio.sleep(1)
                if game_code not in self.games: return
                game["timer"] -= 1
                if game["timer"] <= 0:
                    break
                await self.broadcast_room_state(game_code)

            # Return back to lobby after voting or conclude
            game["state"] = "lobby"
            game["sub_state"] = "none"
            await self.broadcast_room_state(game_code)

        except asyncio.CancelledError:
            pass

    async def connect(self, game_code: str, player_id: str, websocket: WebSocket):
        await websocket.accept()
        if game_code not in self.connections:
            self.connections[game_code] = {}
        
        # Close existing socket if already connected (prevent duplicate ghost instances)
        if player_id in self.connections[game_code]:
            try:
                await self.connections[game_code][player_id].close()
            except:
                pass

        self.connections[game_code][player_id] = websocket
        await self.broadcast_room_state(game_code)

    def disconnect(self, game_code: str, player_id: str):
        if game_code in self.connections and player_id in self.connections[game_code]:
            del self.connections[game_code][player_id]
        
        if game_code in self.games:
            game = self.games[game_code]
            if player_id in game["players"]:
                del game["players"][player_id]
            
            # If host left, assign new host if players remain
            if game["host"] == player_id:
                if game["players"]:
                    game["host"] = list(game["players"].keys())[0]
                else:
                    if game_code in self.tasks:
                        self.tasks[game_code].cancel()
                    del self.games[game_code]

    async def broadcast_room_state(self, game_code: str):
        if game_code not in self.games:
            return
        
        game = self.games[game_code]
        conn_dict = self.connections.get(game_code, {})

        current_turn_id = None
        current_turn_name = ""
        if game["sub_state"] == "discussion" and game["turn_order"]:
            current_turn_id = game["turn_order"][game["turn_index"]]
            current_turn_name = game["players"].get(current_turn_id, {}).get("name", "")

        for pid, ws in conn_dict.items():
            player_info = game["players"].get(pid, {})
            state_data = {
                "type": "room_state",
                "game_code": game_code,
                "is_host": (game["host"] == pid),
                "state": game["state"],
                "sub_state": game["sub_state"],
                "players": [{ "id": p_id, "name": p_val["name"], "eliminated": p_val["eliminated"] } for p_id, p_val in game["players"].items()],
                "my_word": player_info.get("word", ""),
                "current_turn_id": current_turn_id,
                "current_turn_name": current_turn_name,
                "messages": game["messages"],
                "timer": game["timer"]
            }
            try:
                await ws.send_json(state_data)
            except:
                pass

    async def handle_action(self, game_code: str, player_id: str, data: dict):
        action = data.get("action")
        game = self.games.get(game_code)
        if not game:
            return

        if action == "start_game" and game["host"] == player_id:
            success = self.start_game(game_code)
            if success:
                await self.broadcast_room_state(game_code)

        elif action == "send_hint" and game["sub_state"] == "discussion":
            if game["turn_order"] and game["turn_order"][game["turn_index"]] == player_id:
                text = data.get("text", "").strip()
                if text:
                    p_name = game["players"][player_id]["name"]
                    game["messages"].append({"name": p_name, "text": text})
                    # Advance turn
                    game["turn_index"] = (game["turn_index"] + 1) % len(game["turn_order"])
                    if game["turn_index"] == 0:
                        game["sub_state"] = "voting"
                        game["timer"] = 15
                        game["votes"] = {}
                    else:
                        game["timer"] = 20
                    await self.broadcast_room_state(game_code)

        elif action == "vote" and game["sub_state"] == "voting":
            target_id = data.get("target_id")
            if target_id in game["players"] and not game["players"][player_id]["eliminated"]:
                game["votes"][player_id] = target_id
                # If all non-eliminated players voted, resolve early
                active_players = [pid for pid, p in game["players"].items() if not p["eliminated"]]
                if len(game["votes"]) >= len(active_players):
                    # Tally votes
                    tally = {}
                    for v_target in game["votes"].values():
                        tally[v_target] = tally.get(v_target, 0) + 1
                    if tally:
                        max_voted = max(tally, key=tally.get)
                        game["players"][max_voted]["eliminated"] = True
                    game["state"] = "lobby"
                    game["sub_state"] = "none"
                    if game_code in self.tasks:
                        self.tasks[game_code].cancel()
                    await self.broadcast_room_state(game_code)

game_manager = GameManager()
