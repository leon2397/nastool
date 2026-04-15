const WebSocket = require('ws');
const ws = new WebSocket('ws://127.0.0.1:18888/ws/agent?key=test-key');

ws.on('open', function open() {
  console.log('✅ 本地连接成功!');
  ws.close();
});

ws.on('message', function incoming(data) {
  console.log('收到:', data.toString());
});

ws.on('error', function error(err) {
  console.log('❌ 错误:', err.message);
});

ws.on('close', function close() {
  console.log('连接已关闭');
});

setTimeout(() => {
  console.log('超时测试结束');
  process.exit(0);
}, 5000);
