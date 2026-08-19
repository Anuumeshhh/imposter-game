let playerName = "";
let playerId = "";
let gameCode = "";
let ws = null;
let isJoining = false;

let pendingVoteTargetId = null;
let pendingVoteTargetName = "";
let hasVotedThisRound = false;

let pendingModalAction = null;

const screenName = document.getElementById("screen-name");
const screenMenu = document.getElementById("screen-menu");
const screenLobby = document.getElementById("screen-lobby");
const screenGame = document.getElementById("screen-game");

const viewReveal = document.getElementById("view-reveal");
const viewSpeaking = document.getElementById("view-speaking");
const viewAnnouncement = document.getElementById("view-announcement");
const viewVoting = document.getElementById("view-voting");
const viewGameover = document.getElementById("view-gameover");

// Modal control
function showModal(title, desc, onConfirm) {
    document.getElementById("modal-title").innerText = title;
    document.getElementById("modal-desc").innerText = desc;
    pendingModalAction = onConfirm;
    document.getElementById("modal-overlay").classList.remove("hidden");
}

document.getElementById("modal-btn-confirm").addEventListener("click", () => {
    document.getElementById("modal-overlay").classList.add("hidden");
    if (pendingModalAction) pendingModalAction();
});

document.getElementById("modal-btn-cancel").addEventListener("click", () => {
    document.getElementById("modal-overlay").classList.add("hidden");
    pendingModalAction = null;
});

// Name Editing
function promptChangeName() {
    const newName = prompt("Enter your new nickname:", playerName);
    if (newName && newName.trim()) {
        playerName = newName.trim();
        document.getElementById("welcome-msg").innerText = `Welcome, ${playerName}`;
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ action: "change_name", new_name: playerName }));
        }
    }
}

document.getElementById("btn-change-name-menu").addEventListener("click", promptChangeName);
document.getElementById("btn-change-name-lobby").addEventListener("click", promptChangeName);

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

document.getElementById("btn-leave-lobby").addEventListener("click", () => {
    showModal("Leave Room?", "You will exit back to the main menu.", resetToMenu);
});

document.getElementById("btn-leave-game").addEventListener("click", () => {
    showModal("Leave Game?", "Are you sure you want to leave mid-game?", () => {
        if (ws) ws.send(JSON.stringify({ action: "leave_game" }));
        resetToMenu();
    });
});

document.getElementById("btn-back-lobby").addEventListener("click", () => {
    if (ws) ws.send(JSON.stringify({ action: "back_to_lobby" }));
});

document.getElementById("btn-finish-turn").addEventListener("click", () => {
    if (ws) ws.send(JSON.stringify({ action: "finish_turn" }));
});

function resetToMenu() {
    if (ws) {
        ws.close();
        ws = null;
    }
    gameCode = "";
    playerId = "";
    isJoining = false;
    hasVotedThisRound = false;
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
        hasVotedThisRound = false;
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
                hasVotedThisRound = false;
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
                
                document.getElementById("btn-finish-turn").innerText = 
                    `Finish Turn (${data.skip_votes || 0}/${data.skip_votes_needed || 1})`;

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
                const confirmBox = document.getElementById("voting-confirm-box");
                const statusBox = document.getElementById("voting-status-box");

                if (hasVotedThisRound || data.my_vote) {
                    vList.classList.add("hidden");
                    confirmBox.classList.add("hidden");
                    statusBox.classList.remove("hidden");
                    document.getElementById("voting-subtext").classList.add("hidden");
                    document.getElementById("voted-status-text").innerText = `You voted for ${data.my_vote_name || "a player"}. Waiting for others...`;
                } else {
                    statusBox.classList.add("hidden");
                    document.getElementById("voting-subtext").classList.remove("hidden");

                    if (!pendingVoteTargetId) {
                        vList.classList.remove("hidden");
                        confirmBox.classList.add("hidden");
                        vList.innerHTML = "";
                        
                        (data.players || []).forEach(p => {
                            if (!p.eliminated) {
                                const btn = document.createElement("button");
                                btn.className = "vote-btn";
                                btn.innerText = p.id === playerId ? `Vote Yourself (${p.name})` : `Vote ${p.name}`;
                                btn.onclick = () => {
                                    pendingVoteTargetId = p.id;
                                    pendingVoteTargetName = p.name;
                                    updateUIState(data);
                                };
                                vList.appendChild(btn);
                            }
                        });
                    } else {
                        vList.classList.add("hidden");
                        confirmBox.classList.remove("hidden");
                        document.getElementById("voting-confirm-text").innerText = `Are you sure you want to vote ${pendingVoteTargetName}?`;
                    }
                }
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

            document.getElementById("btn-back-lobby").style.display = data.is_host ? "inline-block" : "none";
        }
    }
}

document.getElementById("btn-confirm-vote").addEventListener("click", () => {
    if (pendingVoteTargetId && ws) {
        ws.send(JSON.stringify({ action: "vote", target_id: pendingVoteTargetId }));
        hasVotedThisRound = true;
        pendingVoteTargetId = null;
        pendingVoteTargetName = "";
    }
});

document.getElementById("btn-cancel-vote").addEventListener("click", () => {
    pendingVoteTargetId = null;
    pendingVoteTargetName = "";
    document.getElementById("voting-confirm-box").classList.add("hidden");
    document.getElementById("voting-list").classList.remove("hidden");
});

document.getElementById("btn-start").addEventListener("click", () => {
    if (ws) ws.send(JSON.stringify({ action: "start_game" }));
});
