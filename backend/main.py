import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
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


class CreateGameRequest(BaseModel):
    host_name: str
    mode: str = "single"


class JoinGameRequest(BaseModel):
    game_code: str
    player_name: str


@app.post("/api/create-game")
async def create_game(req: CreateGameRequest):
    name = req.host_name.strip()
    if not name:
        return JSONResponse(status_code=400, content={"error": "Please enter a name."})

    room, player = game_manager.create_room(name, req.mode)
    return {"game_code": room.code, "player_id": player.id}


@app.post("/api/join-game")
async def join_game(req: JoinGameRequest):
    # NOTE: FastAPI does NOT support Flask-style `return body, status_code`.
    # Returning a tuple here used to get serialized as a 200 OK response
    # containing a JSON array, so the frontend's `if (!res.ok)` check never
    # caught it -- callers silently got `data.game_code === undefined` and
    # a websocket connection that immediately failed. Always use an explicit
    # JSONResponse (or raise HTTPException) for error paths.
    room = game_manager.get_room(req.game_code)
    if not room or room.state != "lobby":
        return JSONResponse(
            status_code=400,
            content={"error": "Game not found or already started."},
        )

    name = req.player_name.strip()
    if not name:
        return JSONResponse(status_code=400, content={"error": "Please enter a name."})

    if room.name_taken(name):
        return JSONResponse(
            status_code=409,
            content={"error": f'"{name}" is already taken in this room. Pick a different name.'},
        )

    player = room.add_player(name, is_host=False)
    return {"game_code": room.code, "player_id": player.id}


@app.websocket("/ws/{game_code}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, game_code: str, player_id: str):
    await websocket.accept()
    room = game_manager.get_room(game_code)

    if not room or player_id not in room.players:
        await websocket.send_json({"type": "error", "message": "Room or player not found."})
        await websocket.close()
        return

    player = room.players[player_id]

    # A dropped connection (wifi blip, backgrounded tab, proxy idle timeout,
    # etc.) doesn't delete the player anymore -- see Room.mark_disconnected.
    # Reattach this new socket to that same player instead of treating it as
    # a brand new join, and close out any stale old socket still attached.
    old_ws = room.reconnect_player(player_id, websocket)
    if old_ws and old_ws is not websocket:
        try:
            await old_ws.close()
        except Exception:
            pass

    await room.broadcast_state()

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "ping":
                # Heartbeat only -- keeps the socket "active" so reverse
                # proxies / load balancers with idle timeouts don't kill it
                # while sitting quietly in the lobby.
                continue

            elif action == "activate_admin":
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
                min_players = 5 if room.mode == "double" else 3
                if len(room.players) >= min_players:
                    room.start_game()

            elif action == "finish_turn" and not player.eliminated:
                await room.finish_turn(player_id)

            elif action == "vote" and not player.eliminated:
                target_id = data.get("target_id")
                await room.record_vote(player_id, target_id)

            elif action == "back_to_lobby":
                room.reset_to_lobby()

            elif action == "leave_game":
                room.remove_player(player_id)
                await room.broadcast_state()
                break

    except WebSocketDisconnect:
        room.mark_disconnected(player_id)
        await room.broadcast_state()


@app.get("/")
async def read_index():
    if os.path.exists("frontend/index.html"):
        return FileResponse("frontend/index.html")
    return {"status": "Backend running", "error": "frontend/index.html not found"}


if os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
