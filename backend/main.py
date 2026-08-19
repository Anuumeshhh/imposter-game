import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.game import game_manager

app = FastAPI(title="Imposter Game Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CreateGameRequest(BaseModel):
    host_name: str

class JoinGameRequest(BaseModel):
    game_code: str
    player_name: str

@app.post("/api/create-game")
def create_game(data: CreateGameRequest):
    player_id = str(uuid.uuid4())
    game_code = game_manager.create_room(player_id, data.host_name)
    return {"game_code": game_code, "player_id": player_id}

@app.post("/api/join-game")
def join_game(data: JoinGameRequest):
    game_code = data.game_code.upper()
    if not game_manager.room_exists(game_code):
        raise HTTPException(status_code=404, detail="Game room not found")

    player_id = str(uuid.uuid4())
    success = game_manager.add_player(game_code, player_id, data.player_name)
    if not success:
        raise HTTPException(status_code=400, detail="Could not join room")

    return {"game_code": game_code, "player_id": player_id}

@app.websocket("/ws/{game_code}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, game_code: str, player_id: str):
    await game_manager.connect(game_code, player_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await game_manager.handle_action(game_code, player_id, data)
    except WebSocketDisconnect:
        game_manager.disconnect(game_code, player_id)
        await game_manager.broadcast_room_state(game_code)

# Mount frontend static files so backend can serve the full website
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")