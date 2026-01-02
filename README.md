Voice Room (WebRTC) — Setup and usage

This workspace adds a simple voice-room feature to `index.html` plus a minimal signaling server.

Files added:
- `server.js` — minimal WebSocket signaling server (port 3000)
- `package.json` — dependency manifest for the server
- `index.html` — updated with a "Voice Room" tab (connects to ws://localhost:3000)

Run the signaling server (Node.js required):

```bash
cd "c:\Users\Woody\Documents\Visual studio code folder\HTMLs"
npm install
npm start
```

Serve `index.html` from localhost (required for getUserMedia/autoplay). Options:

- Using a quick static server with npx http-server:

```bash
npx http-server -p 8080
# then open http://localhost:8080/index.html
```

- Or use VS Code Live Server extension and open the file from http://127.0.0.1:5500/...

How to use the voice room:

- One person clicks "Host" to create a room. They get a room code.
- Host shares the room code with friends.
- Friends enter the code and click "Join".
- The microphone toggle enables/disables the local mic. Participants will see each other in the Participants list and hear each other's audio.

Notes and limitations:
- This is a simple mesh-based WebRTC implementation (every participant connects directly to every other). For large groups this will not scale.
- The signaling server is intentionally minimal — it only helps peers exchange offers/answers/ICE candidates and manages rooms.
- For remote usage across NATs/strict networks you may need TURN servers; currently only a public STUN server is used.
- The code assumes you run the signaling server locally at `ws://localhost:3000` and serve `index.html` over `http://localhost`.

If you want, I can:
- Add TURN server support
- Add UI improvements (participant mute icons, reconnect logic)
- Package the server into a simple npm script that launches both the server and a static file server
