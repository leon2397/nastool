const WebSocket = require("ws");
const ws = new WebSocket("ws://198.19.105.56:18888/ws/agent?key=ak_789c561c5793406780c7d383b072a1eb");

ws.on("open", () => console.log("CONNECTED"));
ws.on("message", (data) => console.log("MSG:", data.toString()));
ws.on("error", (err) => console.log("ERROR:", err.message));
ws.on("close", () => console.log("CLOSED"));

setTimeout(() => {
    console.log("TIMEOUT - exiting");
    process.exit(0);
}, 5000);
