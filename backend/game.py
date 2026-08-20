import asyncio
import json
import random
import string
from typing import Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

# Import word logic/list from word.py
from words import get_random_word_pair  

app = FastAPI()

rooms: Dict[str, dict] = {}

class CreateGameReq(BaseModel):
    host_name: str

class JoinGameReq(BaseModel):
    game_code: str
    player_name: str

def generate_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_id(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

@app.post("/api/create-game")
async def create_game(req: CreateGameReq):
    game_code = generate_code()
    host_id = generate_id()
    rooms[game_code] = {
        "game_code": game_code,
        "host_id": host_id,
        "state": "lobby",
        "sub_state": None,
        "players": [
            {
                "id": host_id,
                "name": req.host_name,
                "ws": None,
                "is_bot": False,
                "is_admin": False,
                "eliminated": False,
                "vote": None
            }
        ],
        "current_turn_index": 0,
        "current_round": 1,
        "total_rounds": 2,
        "timer": 0,
        "common_word": "",
        "imposter_word": "",
        "imposter_id": None,
        "votes": {},
        "skip_turn_votes": set()
    }
    return {"game_code": game_code, "player_id": host_id}

@app.post("/api/join-game")
async def join_game(req: JoinGameReq):
    code = req.game_code.upper()
    if code not in rooms:
        raise HTTPException(status_code=404, detail="Game not found")
    
    room = rooms[code]
    if room["state"] != "lobby":
        raise HTTPException(status_code=400, detail="Game already started")

    player_id = generate_id()
    room["players"].append({
        "id": player_id,
        "name": req.player_name,
        "ws": None,
        "is_bot": False,
        "is_admin": False,
        "eliminated": False,
        "vote": None
    })
    return {"game_code": code, "player_id": player_id}

def reset_voting(room):
    """Wipes all active votes across sets, tiebreakers, and new rounds."""
    room["votes"] = {}
    for p in room["players"]:
        p["vote"] = None

async def broadcast_room_state(game_code: str):
    if game_code not in rooms:
        return
    room = rooms[game_code]
    
    for p in room["players"]:
        if p["is_bot"] or p["ws"] is None:
            continue
            
        my_vote_target_id = room["votes"].get(p["id"])
        my_vote_target_name = None
        if my_vote_target_id == "SKIP":
            my_vote_target_name = "Skip Vote"
        elif my_vote_target_id:
            target_p = next((tp for tp in room["players"] if tp["id"] == my_vote_target_id), None)
            if target_p:
                my_vote_target_name = target_p["name"]

        my_word = "???"
        if room["state"] == "playing":
            if p["id"] == room["imposter_id"]:
                my_word = room["imposter_word"]
            else:
                my_word = room["common_word"]

        current_speaker = None
        if room["state"] == "playing" and room["sub_state"] == "speaking":
            active_players = [ap for ap in room["players"] if not ap["eliminated"]]
            if active_players and room["current_turn_index"] < len(active_players):
                current_speaker = active_players[room["current_turn_index"]]

        payload = {
            "type": "room_state",
            "game_code": room["game_code"],
            "state": room["state"],
            "sub_state": room["sub_state"],
            "is_host": (p["id"] == room["host_id"]),
            "timer": room["timer"],
            "current_round": room["current_round"],
            "total_rounds": room["total_rounds"],
            "my_word": my_word,
            "current_turn_id": current_speaker["id"] if current_speaker else None,
            "current_turn_name": current_speaker["name"] if current_speaker else None,
            "skip_votes": len(room["skip_turn_votes"]),
            "skip_votes_needed": (len([ap for ap in room["players"] if not ap["eliminated"]]) // 2) + 1,
            "my_vote": my_vote_target_id,
            "my_vote_name": my_vote_target_name,
            "players": [
                {
                    "id": pl["id"],
                    "name": pl["name"],
                    "is_host": (pl["id"] == room["host_id"]),
                    "is_admin": pl.get("is_admin", False),
                    "is_bot": pl.get("is_bot", False),
                    "eliminated": pl.get("eliminated", False)
                } for pl in room["players"]
            ]
        }

        if room["state"] == "game_over":
            imposter_p = next((ip for ip in room["players"] if ip["id"] == room["imposter_id"]), None)
            payload["winner"] = room.get("winner")
            payload["end_msg"] = room.get("end_msg", "")
            payload["imposter_name"] = imposter_p["name"] if imposter_p else "Unknown"
            payload["common_word"] = room["common_word"]
            payload["imposter_word"] = room["imposter_word"]

        try:
            await p["ws"].send_text(json.dumps(payload))
        except Exception:
            pass

def start_next_turn(room):
    active_players = [p for p in room["players"] if not p["eliminated"]]
    room["skip_turn_votes"] = set()
    
    if room["current_turn_index"] + 1 < len(active_players):
        room["current_turn_index"] += 1
    else:
        room["current_turn_index"] = 0
        if room["current_round"] < room["total_rounds"]:
            room["current_round"] += 1
        else:
            start_voting_phase(room)

def start_voting_phase(room):
    room["sub_state"] = "voting"
    reset_voting(room)

def process_voting_results(room):
    active_players = [p for p in room["players"] if not p["eliminated"]]
    vote_counts = {p["id"]: 0 for p in active_players}
    skips = 0

    for p in active_players:
        if p["is_bot"] and p["id"] not in room["votes"]:
            room["votes"][p["id"]] = "SKIP"

    for voter_id, target_id in room["votes"].items():
        if target_id == "SKIP":
            skips += 1
        elif target_id in vote_counts:
            vote_counts[target_id] += 1

    most_voted_id = None
    max_votes = 0
    is_tie = False

    for target_id, count in vote_counts.items():
        if count > max_votes:
            max_votes = count
            most_voted_id = target_id
            is_tie = False
        elif count == max_votes and max_votes > 0:
            is_tie = True

    if is_tie or max_votes <= skips or not most_voted_id:
        room["sub_state"] = "speaking"
        room["current_round"] = 1
        room["total_rounds"] = 1
        room["current_turn_index"] = 0
        reset_voting(room)
    else:
        ejected_p = next((p for p in room["players"] if p["id"] == most_voted_id), None)
        if ejected_p:
            ejected_p["eliminated"] = True
            if ejected_p["id"] == room["imposter_id"]:
                room["state"] = "game_over"
                room["winner"] = "crew"
                room["end_msg"] = f"{ejected_p['name']} was the Imposter!"
            else:
                remaining_active = [p for p in room["players"] if not p["eliminated"]]
                if len(remaining_active) <= 2:
                    room["state"] = "game_over"
                    room["winner"] = "imposter"
                    room["end_msg"] = f"{ejected_p['name']} was innocent. Imposter took over!"
                else:
                    room["sub_state"] = "speaking"
                    room["current_round"] = 1
                    room["total_rounds"] = 2
                    room["current_turn_index"] = 0
                    reset_voting(room)

@app.websocket("/ws/{game_code}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, game_code: str, player_id: str):
    await websocket.accept()
    if game_code not in rooms:
        await websocket.close()
        return

    room = rooms[game_code]
    player = next((p for p in room["players"] if p["id"] == player_id), None)
    if not player:
        await websocket.close()
        return

    player["ws"] = websocket
    await broadcast_room_state(game_code)

    try:
        while True:
            data_str = await websocket.receive_text()
            data = json.loads(data_str)
            action = data.get("action")

            if action == "activate_admin":
                player["is_admin"] = True
                await broadcast_room_state(game_code)

            elif action == "add_bot":
                if player["id"] == room["host_id"]:
                    bot_num = len([p for p in room["players"] if p["is_bot"]]) + 1
                    room["players"].append({
                        "id": f"bot_{generate_id(4)}",
                        "name": f"Bot {bot_num}",
                        "ws": None,
                        "is_bot": True,
                        "is_admin": False,
                        "eliminated": False,
                        "vote": None
                    })
                    await broadcast_room_state(game_code)

            elif action == "remove_bot":
                if player["id"] == room["host_id"]:
                    bot = next((p for p in reversed(room["players"]) if p["is_bot"]), None)
                    if bot:
                        room["players"].remove(bot)
                        await broadcast_room_state(game_code)

            elif action == "start_game":
                if player["id"] == room["host_id"] and len(room["players"]) >= 3:
                    # Fetch pair from word.py helper or list
                    common, imposter_w = get_random_word_pair()
                    room["common_word"] = common
                    room["imposter_word"] = imposter_w

                    imposter = random.choice(room["players"])
                    room["imposter_id"] = imposter["id"]
                    
                    for p in room["players"]:
                        p["eliminated"] = False
                        p["vote"] = None
                    
                    room["state"] = "playing"
                    room["sub_state"] = "reveal"
                    room["current_round"] = 1
                    room["total_rounds"] = 2
                    room["current_turn_index"] = 0
                    reset_voting(room)
                    await broadcast_room_state(game_code)

                    await asyncio.sleep(4)
                    if room["state"] == "playing" and room["sub_state"] == "reveal":
                        room["sub_state"] = "speaking"
                        await broadcast_room_state(game_code)

            elif action == "finish_turn":
                if room["sub_state"] == "speaking":
                    active_players = [p for p in room["players"] if not p["eliminated"]]
                    current_speaker = active_players[room["current_turn_index"]] if active_players else None

                    if (current_speaker and player["id"] == current_speaker["id"]) or player["is_bot"]:
                        start_next_turn(room)
                    else:
                        room["skip_turn_votes"].add(player["id"])
                        needed = (len(active_players) // 2) + 1
                        if len(room["skip_turn_votes"]) >= needed:
                            start_next_turn(room)
                            
                    await broadcast_room_state(game_code)

            elif action == "vote":
                if room["sub_state"] == "voting":
                    target_id = data.get("target_id")
                    room["votes"][player["id"]] = target_id
                    player["vote"] = target_id

                    active_players = [p for p in room["players"] if not p["eliminated"]]
                    human_votes = len(room["votes"])
                    bot_count = len([p for p in active_players if p["is_bot"]])

                    if human_votes + bot_count >= len(active_players):
                        process_voting_results(room)

                    await broadcast_room_state(game_code)

            elif action == "back_to_lobby":
                if player["id"] == room["host_id"]:
                    room["state"] = "lobby"
                    room["sub_state"] = None
                    reset_voting(room)
                    await broadcast_room_state(game_code)

            elif action == "leave_game":
                room["players"].remove(player)
                if not room["players"]:
                    rooms.pop(game_code, None)
                else:
                    if room["host_id"] == player["id"]:
                        room["host_id"] = room["players"][0]["id"]
                    await broadcast_room_state(game_code)
                break

    except WebSocketDisconnect:
        if player in room["players"]:
            room["players"].remove(player)
            if not room["players"]:
                rooms.pop(game_code, None)
            else:
                if room["host_id"] == player["id"]:
                    room["host_id"] = room["players"][0]["id"]
                await broadcast_room_state(game_code)
