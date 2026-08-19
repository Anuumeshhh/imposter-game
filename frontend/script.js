let playerName = "";
let playerId = "";
let gameCode = "";
let ws = null;
let isJoining = false;

const screenName = document.getElementById("screen-name");
const screenMenu = document.getElementById("screen-menu");
const screenLobby = document.getElementById("screen-lobby");
const screenGame = document.getElementById("screen-game");

const viewReveal = document.getElementById("view-reveal");
const viewSpeaking = document.getElementById("view-speaking");
const viewAnnouncement = document.getElementById("view-announcement");
const viewVoting = document.getElementById("view-voting");
const viewGameover = document.getElementById("view-gameover");

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
    if (isJoining) return;
    const code = document.getElementById("input-code").value.trim().toUpperCase();
    if (!code) return alert("Enter a game code");
    
    isJoining = true;
    const joinBtn = document.getElementById("btn-join");
    joinBtn.disabled = true;

    try {
        const res = await fetch("/api/join-game", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ game_code: code, player_name: playerName })
        });
        if (!res.ok) throw new Error();
        const data = await res.json();
        gameCode = data.game_code;
        playerId = data.player_id;
        connectWebSocket();
    } catch (err) {
        alert("Game not found or already started");
        isJoining = false;
        joinBtn.disabled = false;
    }
});

document.getElementById("btn-leave").addEventListener("click", () => {
    resetToMenu();
});

document.getElementById("btn-back-lobby").addEventListener("click", () => {
    if (ws) {
        ws.send(JSON.stringify({ action: "back_to_lobby" }));
    }
});

function resetToMenu() {
    if (ws) {
        ws.close();
        ws = null;
    }
    gameCode = "";
    playerId = "";
    isJoining = false;
    document.getElementById("btn-join").disabled = false;
    screenLobby.classList.add("hidden");
    screenGame.classList.add("hidden");
    screenMenu.classList.remove("hidden");
}

function connectWebSocket() {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${proto}//${window.location.host}/ws/${gameCode}/${playerId}`);

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "room_state") {
            updateUIState(data);
        }
    };

    ws.onclose = () => { resetToMenu(); };
}

function hideAllViews() {
    viewReveal.classList.add("hidden");
    viewSpeaking.classList.add("hidden");
    viewAnnouncement.classList.add("hidden");
    viewVoting.classList.add("hidden");
    viewGameover.classList.add("hidden");
}

function updateUIState(data) {
    screenMenu.classList.add("hidden");
    isJoining = false;
    document.getElementById("btn-join").disabled = false;
    
    if (data.state === "lobby") {
        screenLobby.classList.remove("hidden");
        screenGame.classList.add("hidden");
        
        document.getElementById("display-code").innerText = data.game_code;
        
        const list = document.getElementById("player-list");
        list.innerHTML = "";
        data.players.forEach(p => {
            const li = document.createElement("li");
            li.innerHTML = `● <strong>${p.name}</strong>`;
            list.appendChild(li);
        });

        const startBtn = document.getElementById("btn-start");
        const statusEl = document.getElementById("lobby-status");
        
        if (data.is_host) {
            startBtn.classList.remove("hidden");
            if (data.players.length < 3) {
                startBtn.disabled = true;
                startBtn.style.opacity = "0.5";
                statusEl.innerText = `Need at least 3 players (${data.players.length}/3)`;
            } else {
                startBtn.disabled = false;
                startBtn.style.opacity = "1";
                statusEl.innerText = "Ready to start game!";
            }
        } else {
            startBtn.classList.add("hidden");
            statusEl.innerText = data.players.length < 3 
                ? `Waiting for players (${data.players.length}/3)...` 
                : "Waiting for host to start...";
        }
    } else if (data.state === "playing" || data.state === "game_over") {
        screenLobby.classList.add("hidden");
        screenGame.classList.remove("hidden");
        hideAllViews();

        document.getElementById("turn-timer").innerText = `${data.timer || 0}s`;

        if (data.state === "playing") {
            if (data.sub_state === "reveal") {
                viewReveal.classList.remove("hidden");
                document.getElementById("secret-word").innerText = data.my_word;
                document.getElementById("game-round-indicator").innerText = "REVEAL PHASE";
            } 
            else if (data.sub_state === "speaking") {
                viewSpeaking.classList.remove("hidden");
                document.getElementById("game-round-indicator").innerText = `ROUND ${data.current_round}/${data.total_rounds}`;
                
                const speakerNameEl = document.getElementById("speaker-name");
                if (data.current_turn_id === playerId) {
                    speakerNameEl.innerText = "YOUR TURN!";
                } else {
                    speakerNameEl.innerText = data.current_turn_name;
                }
                document.getElementById("reminder-word").innerText = data.my_word;
            } 
            else if (data.sub_state === "announcement") {
                viewAnnouncement.classList.remove("hidden");
                document.getElementById("announcement-title").innerText = data.announcement_text;
                document.getElementById("game-round-indicator").innerText = "ANNOUNCEMENT";
            } 
            else if (data.sub_state === "voting") {
                viewVoting.classList.remove("hidden");
                document.getElementById("game-round-indicator").innerText = "VOTING PHASE";

                const vList = document.getElementById("voting-list");
                vList.innerHTML = "";
                
                (data.players || []).forEach(p => {
                    if (p.id !== playerId && !p.eliminated) {
                        const btn = document.createElement("button");
                        btn.className = "vote-btn";
                        btn.innerText = `Vote ${p.name}`;
                        btn.onclick = () => {
                            ws.send(JSON.stringify({ action: "vote", target_id: p.id }));
                            vList.innerHTML = "<p class='hint-text'>Vote submitted! Waiting for others...</p>";
                        };
                        vList.appendChild(btn);
                    }
                });
            }
        } 
        else if (data.state === "game_over") {
            viewGameover.classList.remove("hidden");
            document.getElementById("game-round-indicator").innerText = "GAME OVER";

            const titleEl = document.getElementById("game-result-title");
            if (data.winner === "crew") {
                titleEl.className = "win-title";
                titleEl.innerText = "VICTORY! CREWMATES WIN!";
            } else {
                titleEl.className = "lose-title";
                titleEl.innerText = "DEFEAT! IMPOSTER WINS!";
            }

            document.getElementById("game-result-desc").innerText = data.end_msg || "";
            document.getElementById("reveal-imposter-name").innerText = data.imposter_name || "--";
            document.getElementById("reveal-common-word").innerText = data.common_word || "--";
            document.getElementById("reveal-imposter-word").innerText = data.imposter_word || "--";

            const backBtn = document.getElementById("btn-back-lobby");
            if (data.is_host) {
                backBtn.style.display = "inline-block";
            } else {
                backBtn.style.display = "none";
            }
        }
    }
}

document.getElementById("btn-start").addEventListener("click", () => {
    if (ws) {
        ws.send(JSON.stringify({ action: "start_game" }));
    }
});
