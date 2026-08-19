# 🕵️‍♂️ Imposter Game (Web-Based Social Deduction Game)

> A real-time, multiplayer social deduction web game built with **Python FastAPI**, **WebSockets**, and **Vanilla JavaScript**. Inspired by undercover word games, players receive secret words (or are assigned as the imposter) and must figure out who is who through clues, chat, and deduction!

No heavy frontend frameworks, no databases required, and no user accounts to create—just spin up a room, share the code, and play instantly right in your mobile or desktop browser! 🚀

---

## 🌟 Features

* **⚡ Real-time Synchronization:** Powered by WebSockets so lobbies, player lists, and game actions update instantly across all players' devices.
* **🛡️ Server-Authoritative Logic:** Game rules, secret word distribution, and state transitions are entirely managed on the Python backend to completely prevent cheating or inspection.
* **📱 Mobile-First Design:** Fully responsive layout built to run smoothly on any mobile browser—no app store downloads needed!
* **📦 Lightweight Architecture:** Built cleanly using FastAPI without the bloat of heavy ORMs, complex build pipelines, or databases.

---

## 🎮 How to Play

1. **Enter Your Name:** Open the website and type in your nickname.
2. **Create or Join:** 
   * Create a new room to get a unique **4-character Game Code** (e.g., `K7P2`).
   * Or enter a friend's code to join their lobby.
3. **The Reveal:** Once the host starts the game, the server secretly assigns a common word to crew members and a different (but related) word to the single **Imposter**.
4. **Discussion & Voting:** Give hints, chat in real-time, and vote out who you think the imposter is!

---

## 📁 Project Structure

```text
imposter-game/
│
├── backend/
│   ├── __init__.py
│   ├── main.py        # FastAPI app, static file mounting, & WebSocket routing
│   ├── game.py        # Core game state manager, rooms, and logic
│   └── words.py       # Curated word pairs with difficulty tiers
│
├── frontend/
│   ├── index.html     # Single-page interface with multiple screens
│   ├── style.css      # Dark-themed responsive styles
│   └── script.js      # WebSocket client and dynamic UI controller
│
└── requirements.txt   # Python dependencies
