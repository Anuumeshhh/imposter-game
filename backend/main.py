import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.game import game_manager

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_index():

    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"status": "Backend running", "message": "index.html not found"}

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


class CreateGameRequest(BaseModel):
    host_name: str


class JoinGameRequest(BaseModel):
    game_code: str
    player_name: str


@app.post("/api/create-game")
async def create_game(req: CreateGameRequest):
    room, player = game_manager.create_room(req.host_name)
    return {"game_code": room.code, "player_id": player.id}


@app.post("/api/join-game")
async def join_game(req: JoinGameRequest):
    room = game_manager.get_room(req.game_code)
    if not room or room.state != "lobby":
        return {"error": "Game not found or already started"}, 400

    player = room.add_player(req.player_name, is_host=False)
    return {"game_code": room.code, "player_id": player.id}


@app.websocket("/ws/{game_code}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, game_code: str, player_id: str):
    await websocket.accept()
    room = game_manager.get_room(game_code)

    if not room or player_id not in room.players:
        await websocket.close()
        return

    player = room.players[player_id]
    player.websocket = websocket
    await room.broadcast_state()

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "activate_admin":
                player.is_admin = True
                await room.broadcast_state()

            elif action == "add_bot" and player.is_admin:
                bot_num = len([p for p in room.players.values() if p.is_bot]) + 1
                room.add_player(f"Bot {bot_num}", is_bot=True)
                await room.broadcast_state()

            elif action == "remove_bot" and player.is_admin:
                bots = [p.id for p in room.players.values() if p.is_bot]
                if bots:
                    room.remove_player(bots[-1])
                    await room.broadcast_state()

            elif action == "start_game" and player.is_host:
                if len(room.players) >= 3:
                    room.start_game()

            elif action == "finish_turn":
                await room.finish_turn(player_id)

            elif action == "vote":
                target_id = data.get("target_id")
                await room.record_vote(player_id, target_id)

            elif action == "back_to_lobby" and player.is_host:
                room.reset_to_lobby()

            elif action == "leave_game":
                room.remove_player(player_id)
                await room.broadcast_state()
                break

    except WebSocketDisconnect:
        room.remove_player(player_id)
        await room.broadcast_state()
