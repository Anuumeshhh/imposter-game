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
const viewPlaying = document.getElementById("view-playing");
const viewVoting = document.getElementById("view-voting");

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
    if (ws) ws.close();
    resetToMenu();
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

    ws.onclose = () => {
        resetToMenu();
    };
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
                ? `Waiting for more players (${data.players.length}/3)...` 
                : "Waiting for host to start...";
        }
    } else if (data.state === "playing" || data.state === "voting") {
        screenLobby.classList.add("hidden");
        screenGame.classList.remove("hidden");

        if (data.sub_state === "reveal") {
            viewReveal.classList.remove("hidden");
            viewPlaying.classList.add("hidden");
            viewVoting.classList.add("hidden");
            document.getElementById("secret-word").innerText = data.my_word;
            document.getElementById("game-phase-indicator").innerText = "Phase: Word Reveal";
        } else if (data.sub_state === "discussion") {
            viewReveal.classList.add("hidden");
            viewPlaying.classList.remove("hidden");
            viewVoting.classList.add("hidden");
            document.getElementById("game-phase-indicator").innerText = "Phase: Hints & Discussion";

            const turnBanner = document.getElementById("turn-banner");
            const hintInputGrp = document.getElementById("hint-input-group");

            if (data.current_turn_id === playerId) {
                turnBanner.innerText = "👉 It is YOUR turn to give a hint!";
                hintInputGrp.style.display = "flex";
            } else {
                turnBanner.innerText = `⏳ Waiting for ${data.current_turn_name} to give a hint...`;
                hintInputGrp.style.display = "none";
            }

            const chatBox = document.getElementById("chat-messages");
            chatBox.innerHTML = "";
            (data.messages || []).forEach(m => {
                const div = document.createElement("div");
                div.className = "chat-msg";
                div.innerHTML = `<span>${m.name}:</span> ${m.text}`;
                chatBox.appendChild(div);
            });
            chatBox.scrollTop = chatBox.scrollHeight;
        } else if (data.sub_state === "voting") {
            viewReveal.classList.add("hidden");
            viewPlaying.classList.add("hidden");
            viewVoting.classList.remove("hidden");
            document.getElementById("game-phase-indicator").innerText = "Phase: Voting";

            const vList = document.getElementById("voting-list");
            vList.innerHTML = "";
            (data.players || []).forEach(p => {
                if (p.id !== playerId && !p.eliminated) {
                    const btn = document.createElement("button");
                    btn.className = "vote-btn";
                    btn.innerText = `Vote ${p.name}`;
                    btn.onclick = () => {
                        ws.send(JSON.stringify({ action: "vote", target_id: p.id }));
                        vList.innerHTML = "<p>Vote submitted! Waiting for others...</p>";
                    };
                    vList.appendChild(btn);
                }
            });
        }

        document.getElementById("turn-timer").innerText = `${data.timer || 0}s`;
    }
}

document.getElementById("btn-start").addEventListener("click", () => {
    if (ws) {
        ws.send(JSON.stringify({ action: "start_game" }));
    }
});

document.getElementById("btn-send-hint").addEventListener("click", () => {
    const hintInput = document.getElementById("input-hint");
    const text = hintInput.value.trim();
    if (!text) return;
    ws.send(JSON.stringify({ action: "send_hint", text: text }));
    hintInput.value = "";
});
