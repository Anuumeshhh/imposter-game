# 🕵️‍♂️ The Imposter Game 🕵️‍♀️

Welcome to **The Imposter Game**! This is a fast-paced, real-time multiplayer social deduction game built for the web. Gather your friends, test your deception skills, and find out who among you is the ultimate imposter! 

In each round, players are secretly assigned a word. The **Crewmates** all receive the exact same common word, while the **Imposter(s)** receives a similar but distinctly different word. Through careful discussion, deduction, and voting, the Crewmates must eliminate the Imposter before it's too late!

---

## ✨ Key Features

*   **⚡ Real-Time Gameplay:** Powered by WebSockets to handle instantaneous state updates, seamless turn-taking, and live voting without page refreshes.
*   **🔄 Unbreakable Connections:** Built-in session storage, periodic heartbeats, and automatic reconnect attempts ensure that if you drop connection (Wi-Fi blip or closed tab), you can instantly rejoin the lobby right where you left off.
*   **🎮 Multiple Game Modes:**
    *   **Single Imposter:** Classic mode for 3 or more players.
    *   **Double Imposter:** Chaos mode for larger groups (requires 5+ players).
*   **🤖 Automated Bots & Admin Controls:** Short on players? The host can seamlessly add AI bots to fill out the lobby (requires admin access). 
*   **📚 Massive Word Database:** Features a diverse, Base64-encoded library of word pairs spanning Anime (JJK, MHA, One Piece, etc.), Marvel, Science, Technology, and everyday items. Base64 encoding ensures source words remain hidden from plain text in the network tab!
*   **🎵 Dynamic Synthesized Audio:** Utilizes the native Web Audio API to generate custom, synthesized sound effects for UI clicks, turn announcements, and game-over states—no external MP3/WAV files required!
*   **🌌 Polished UI & Animations:** A beautiful, responsive dark-themed interface built with custom CSS animations to give phase transitions, countdown timers, and player interactions a weighty, premium feel.

---

## 🛠️ Tech Stack

| Component | Technologies Used |
| :--- | :--- |
| **Frontend** | HTML5, CSS3 (Custom animations, Poppins font), Vanilla JavaScript |
| **Backend** | Python, FastAPI, `asyncio` |
| **Networking** | WebSockets (Live game state), REST APIs (Room creation) |

---

## 🎲 How to Play (Game Flow)

### 1. The Lobby Setup 🚪
A host creates a room, selects the number of imposters, and is given a unique **6-character Room Code**. Share this code with your friends so they can join your lobby.

### 2. The Reveal Phase 🤫
Once everyone is ready, the host starts the game. A secret word is revealed to each player on their screen. Keep it hidden!

### 3. The Speaking Phase 💬
A randomized turn order is established. When it is your turn, you must give a **one-word or short-phrase hint** about your word. 
*   *Crewmate Goal:* Prove you know the word without giving it away to the Imposter.
*   *Imposter Goal:* Blend in and figure out what the Crewmate word is based on their hints!

### 4. The Voting Phase 🗳️
After all turns are complete, players discuss and cast their vote for who they think the Imposter is. You can also choose to **Skip** voting. If there is a tie, an automatic tiebreaker speaking round is triggered!

### 5. Winning the Game 🏆
*   **Crewmates Win:** If the Imposter(s) is successfully voted out.
*   **Imposter Wins:** If they survive until there are 3 or fewer total players remaining in the game.

---

## ⚙️ Admin Controls

For developers and server hosts, there are hidden controls to help manage lobbies and test gameplay.

---

## 🚀 Installation & Local Setup

Want to run The Imposter Game on your local machine? Follow these steps:

### Prerequisites
*   Python 3.8+ installed
*   A modern web browser

### Backend Setup
1. Clone the repository:
   ```bash
   git clone [https://github.com/yourusername/imposter-game.git](https://github.com/yourusername/imposter-game.git)
   cd imposter-game
   ```
2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```
   *The backend will typically run on `http://localhost:8000`.*

### Frontend Setup
1. Navigate to the frontend directory.
2. If using a live server extension (like VS Code Live Server), simply serve the `index.html` file.
3. Ensure the WebSocket connection URL in your `app.js` (or equivalent file) points to your local FastAPI server.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! 
1. Fork the project.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

---
*Happy Deceiving! 🎭*
