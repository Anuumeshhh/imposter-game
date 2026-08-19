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
            "current_round": 1,
            "total_rounds": 2,
            "timer": 0,
            "votes": {},
            "skip_votes": set(),
            "announcement_text": "",
            "imposter_id": None,
            "imposter_name": "",
            "common_word": "",
            "imposter_word": "",
            "winner": None,
            "end_msg": ""
        }
        self.connections[game_code] = {}
        return game_code

    def add_player(self, game_code: str, player_id: str, player_name: str) -> bool:
        if game_code not in self.games:
            return False
        game = self.games[game_code]
        if game["state"] != "lobby":
            return False
        
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

        game["imposter_id"] = imposter_id
        game["imposter_name"] = players[imposter_id]["name"]
        game["common_word"] = common_word
        game["imposter_word"] = imposter_word

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
        
        if game_code in self.tasks:
            self.tasks[game_code].cancel()
        
        self.tasks[game_code] = asyncio.create_task(self.run_game_loop(game_code))
        return True

    def check_game_over(self, game_code: str) -> bool:
        game = self.games.get(game_code)
        if not game or game["state"] != "playing":
            return False

        active_players = [pid for pid, p in game["players"].items() if not p["eliminated"]]
        imposter_id = game["imposter_id"]

        # Imposter left or eliminated
        if imposter_id not in active_players:
            game["state"] = "game_over"
            game["winner"] = "crew"
            game["end_msg"] = "The Imposter was eliminated!"
            return True

        # Imposter equals/outnumbers crewmates
        crew_count = sum(1 for pid in active_players if not game["players"][pid]["is_imposter"])
        if crew_count <= 1:
            game["state"] = "game_over"
            game["winner"] = "imposter"
            game["end_msg"] = f"Imposter ({game['imposter_name']}) takes over!"
            return True

        return False

    async def run_game_loop(self, game_code: str):
        try:
            game = self.games[game_code]
            
            # 1. Secret Word Reveal Phase (5s)
            game["sub_state"] = "reveal"
            game["timer"] = 5
            await self.broadcast_room_state(game_code)
            for _ in range(5):
                await asyncio.sleep(1)
                if game_code not in self.games or game["state"] != "playing": return
                game["timer"] -= 1
                await self.broadcast_room_state(game_code)

            max_rounds = 2  # Default initial cycles: 2 rounds

            while True:
                # 2. Speaking Turns Loop
                for r in range(1, max_rounds + 1):
                    game["sub_state"] = "speaking"
                    game["current_round"] = r
                    game["total_rounds"] = max_rounds
                    
                    active_players = [pid for pid, p in game["players"].items() if not p["eliminated"]]
                    
                    for pid in active_players:
                        if game_code not in self.games or game["state"] != "playing": return
                        if pid not in game["players"] or game["players"][pid]["eliminated"]: continue

                        game["current_turn_id"] = pid
                        game["current_turn_name"] = game["players"][pid]["name"]
                        game["skip_votes"] = set()
                        game["timer"] = 30
                        await self.broadcast_room_state(game_code)

                        for _ in range(30):
                            await asyncio.sleep(1)
                            if game_code not in self.games or game["state"] != "playing": return
                            
                            # Check Majority Skip Turn
                            cur_active = [p_id for p_id, p_val in game["players"].items() if not p_val["eliminated"]]
                            needed = (len(cur_active) // 2) + 1
                            if len(game["skip_votes"]) >= needed:
                                break

                            game["timer"] -= 1
                            await self.broadcast_room_state(game_code)

                if self.check_game_over(game_code):
                    await self.broadcast_room_state(game_code)
                    break

                # 3. Voting Announcement (3s)
                game["sub_state"] = "announcement"
                game["announcement_text"] = "IT'S VOTING TIME!"
                game["timer"] = 3
                await self.broadcast_room_state(game_code)
                for _ in range(3):
                    await asyncio.sleep(1)
                    if game_code not in self.games or game["state"] != "playing": return
                    game["timer"] -= 1
                    await self.broadcast_room_state(game_code)

                # 4. Voting Phase (35s)
                game["sub_state"] = "voting"
                game["timer"] = 35
                game["votes"] = {}
                await self.broadcast_room_state(game_code)

                for _ in range(35):
                    cur_active = [p_id for p_id, p_val in game["players"].items() if not p_val["eliminated"]]
                    if len(game["votes"]) >= len(cur_active):
                        break
                    await asyncio.sleep(1)
                    if game_code not in self.games or game["state"] != "playing": return
                    game["timer"] -= 1
                    await self.broadcast_room_state(game_code)

                # 5. Tally Votes
                tally = {}
                for voter, target in game["votes"].items():
                    tally[target] = tally.get(target, 0) + 1

                top_voted = []
                if tally:
                    max_v = max(tally.values())
                    top_voted = [pid for pid, count in tally.items() if count == max_v]

                if len(top_voted) == 1:
                    eliminated_id = top_voted[0]
                    game["players"][eliminated_id]["eliminated"] = True
                    elim_name = game["players"][eliminated_id]["name"]

                    if self.check_game_over(game_code):
                        await self.broadcast_room_state(game_code)
                        break
                    else:
                        # Non-imposter voted out -> Continue 2-round cycle
                        game["sub_state"] = "announcement"
                        game["announcement_text"] = f"{elim_name} was NOT the Imposter!"
                        game["timer"] = 4
                        await self.broadcast_room_state(game_code)
                        for _ in range(4):
                            await asyncio.sleep(1)
                            if game_code not in self.games or game["state"] != "playing": return
                            game["timer"] -= 1
                            await self.broadcast_room_state(game_code)
                        max_rounds = 2
                else:
                    # Tie vote -> 1 Tie-breaker round
                    game["sub_state"] = "announcement"
                    game["announcement_text"] = "TIE VOTE! 1 Extra Tie-Breaker Round!"
                    game["timer"] = 4
                    await self.broadcast_room_state(game_code)
                    for _ in range(4):
                        await asyncio.sleep(1)
                        if game_code not in self.games or game["state"] != "playing": return
                        game["timer"] -= 1
                        await self.broadcast_room_state(game_code)
                    max_rounds = 1

        except asyncio.CancelledError:
            pass

    async def connect(self, game_code: str, player_id: str, websocket: WebSocket):
        await websocket.accept()
        if game_code not in self.connections:
            self.connections[game_code] = {}
        
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
            
            if game["state"] == "playing":
                if self.check_game_over(game_code):
                    asyncio.create_task(self.broadcast_room_state(game_code))

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

        active_players = [pid for pid, p in game["players"].items() if not p["eliminated"]]
        skip_votes_needed = (len(active_players) // 2) + 1 if active_players else 1

        for pid, ws in conn_dict.items():
            player_info = game["players"].get(pid, {})
            voted_target_id = game.get("votes", {}).get(pid)
            voted_target_name = game["players"].get(voted_target_id, {}).get("name", "") if voted_target_id else ""

            state_data = {
                "type": "room_state",
                "game_code": game_code,
                "is_host": (game["host"] == pid),
                "state": game["state"],
                "sub_state": game["sub_state"],
                "players": [{ "id": p_id, "name": p_val["name"], "eliminated": p_val["eliminated"] } for p_id, p_val in game["players"].items()],
                "my_word": player_info.get("word", ""),
                "current_turn_id": game.get("current_turn_id"),
                "current_turn_name": game.get("current_turn_name"),
                "current_round": game.get("current_round", 1),
                "total_rounds": game.get("total_rounds", 2),
                "skip_votes": len(game.get("skip_votes", set())),
                "skip_votes_needed": skip_votes_needed,
                "my_vote": voted_target_id,
                "my_vote_name": voted_target_name,
                "announcement_text": game.get("announcement_text", ""),
                "winner": game.get("winner"),
                "end_msg": game.get("end_msg"),
                "imposter_name": game.get("imposter_name"),
                "common_word": game.get("common_word"),
                "imposter_word": game.get("imposter_word"),
                "timer": game.get("timer", 0)
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

        if action == "change_name":
            new_name = data.get("new_name", "").strip()
            if new_name and player_id in game["players"]:
                game["players"][player_id]["name"] = new_name
                await self.broadcast_room_state(game_code)

        elif action == "start_game" and game["host"] == player_id:
            success = self.start_game(game_code)
            if success:
                await self.broadcast_room_state(game_code)

        elif action == "finish_turn" and game["sub_state"] == "speaking":
            if not game["players"][player_id]["eliminated"]:
                game["skip_votes"].add(player_id)
                await self.broadcast_room_state(game_code)

        elif action == "vote" and game["sub_state"] == "voting":
            target_id = data.get("target_id")
            if target_id in game["players"] and not game["players"][player_id]["eliminated"]:
                game["votes"][player_id] = target_id
                await self.broadcast_room_state(game_code)

        elif action == "leave_game":
            self.disconnect(game_code, player_id)
            await self.broadcast_room_state(game_code)

        elif action == "back_to_lobby" and game["host"] == player_id:
            if game_code in self.tasks:
                self.tasks[game_code].cancel()
            game["state"] = "lobby"
            game["sub_state"] = "none"
            await self.broadcast_room_state(game_code)

game_manager = GameManager()
