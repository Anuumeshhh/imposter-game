let playerName = "";
let playerId = "";
let gameCode = "";
let ws = null;

const screenName = document.getElementById("screen-name");
const screenMenu = document.getElementById("screen-menu");
const screenLobby = document.getElementById("screen-lobby");
const screenGame = document.getElementById("screen-game");

document.getElementById("btn-save-name").addEventListener("click", () => {
    const val = document.getElementById("input-name").value.trim();
    if (!val) return alert("Please enter a name");
    playerName = val;
    document.getElementById("welcome-msg").innerText = `Welcome, ${playerName}`;
    screenName.classList.add("hidden");
    screenMenu.classList.remove("hidden");
});

document.getElementById("btn-create").addEventListener("click", async () => {
    try {
        const res = await fetch("/api/create-game", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ host_name: playerName })
        });
        const data = await res.json();
        gameCode = data.game_code;
        playerId = data.player_id;
        connectWebSocket();
    } catch (err) {
        alert("Error creating game");
    }
});

document.getElementById("btn-join").addEventListener("click", async () => {
    const code = document.getElementById("input-code").value.trim().toUpperCase();
    if (!code) return alert("Enter a game code");
    
    try {
        const res = await fetch("/api/join-game", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ game_code: code, player_name: playerName })
        });
        const data = await res.json();
        gameCode = data.game_code;
        playerId = data.player_id;
        connectWebSocket();
    } catch (err) {
        alert("Game not found or already started");
    }
});

function connectWebSocket() {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${proto}//${window.location.host}/ws/${gameCode}/${playerId}`);

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "room_state") {
            updateUIState(data);
        }
    };
}

function updateUIState(data) {
    screenMenu.classList.add("hidden");
    
    if (data.state === "lobby") {
        screenLobby.classList.remove("hidden");
        screenGame.classList.add("hidden");
        
        document.getElementById("display-code").innerText = data.game_code;
        
        const list = document.getElementById("player-list");
        list.innerHTML = "";
        data.players.forEach(p => {
            const li = document.createElement("li");
            li.innerText = `● ${p.name}`;
            list.appendChild(li);
        });

        const startBtn = document.getElementById("btn-start");
        if (data.is_host) {
            startBtn.classList.remove("hidden");
        } else {
            startBtn.classList.add("hidden");
            document.getElementById("lobby-status").innerText = "Waiting for host to start...";
        }
    } else if (data.state === "playing") {
        screenLobby.classList.add("hidden");
        screenGame.classList.remove("hidden");
        
        document.getElementById("secret-word").innerText = data.my_word;
    }
}

document.getElementById("btn-start").addEventListener("click", () => {
    if (ws) {
        ws.send(JSON.stringify({ action: "start_game" }));
    }
});