const WebSocket = require('ws');

const wss = new WebSocket.Server({ port: 3000 }, () => {
  console.log('Signaling server listening on ws://localhost:3000');
});

const rooms = {}; // room -> Set of client ids
const clients = {}; // clientId -> { ws, room }

function send(ws, obj) {
  try {
    ws.send(JSON.stringify(obj));
  } catch (e) {
    console.warn('Failed to send', e);
  }
}

function broadcastToRoom(room, obj, exceptId) {
  const set = rooms[room];
  if (!set) return;
  for (const id of set) {
    if (id === exceptId) continue;
    const client = clients[id];
    if (client && client.ws && client.ws.readyState === WebSocket.OPEN) {
      send(client.ws, obj);
    }
  }
}

wss.on('connection', (ws) => {
  const id = Math.random().toString(36).substr(2, 9);
  clients[id] = { ws, room: null };
  send(ws, { type: 'id', id });

  ws.on('message', (raw) => {
    let msg = null;
    try { msg = JSON.parse(raw); } catch (e) { return; }

    const type = msg.type;

    if (type === 'create') {
      const room = String(msg.room).toUpperCase();
      if (!rooms[room]) rooms[room] = new Set();
      rooms[room].add(id);
      clients[id].room = room;
      send(ws, { type: 'created', room });
      console.log(`Client ${id} created room ${room}`);
    } else if (type === 'join') {
      const room = String(msg.room).toUpperCase();
      if (!rooms[room]) {
        // room not found
        send(ws, { type: 'error', message: 'Room not found' });
        return;
      }
      // send existing peers list to joiner
      const peers = Array.from(rooms[room]);
      send(ws, { type: 'joined', room, peers });

      // notify existing peers about the new joiner
      broadcastToRoom(room, { type: 'new-peer', peerId: id }, null);

      rooms[room].add(id);
      clients[id].room = room;
      console.log(`Client ${id} joined room ${room}`);
    } else if (type === 'offer' || type === 'answer' || type === 'ice-candidate') {
      const to = msg.to;
      if (!to) return;
      const target = clients[to];
      if (target && target.ws && target.ws.readyState === WebSocket.OPEN) {
        send(target.ws, msg);
      }
    } else if (type === 'leave') {
      const room = clients[id].room;
      if (room && rooms[room]) {
        rooms[room].delete(id);
        broadcastToRoom(room, { type: 'peer-left', peerId: id }, null);
        clients[id].room = null;
        console.log(`Client ${id} left room ${room}`);
      }
    }
  });

  ws.on('close', () => {
    const info = clients[id];
    if (info && info.room) {
      const room = info.room;
      if (rooms[room]) {
        rooms[room].delete(id);
        broadcastToRoom(room, { type: 'peer-left', peerId: id }, null);
      }
    }
    delete clients[id];
    console.log('Client disconnected', id);
  });
});
