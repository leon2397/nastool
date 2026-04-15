# Relay Server PM2 配置
module.exports = {
  apps: [{
    name: 'nastools-relay',
    script: 'src/index.js',
    cwd: '/root/ai-nas/relay_server',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '256M',
    env: {
      NODE_ENV: 'production',
      PORT: 18888,
      HOST: '0.0.0.0',
      LOG_LEVEL: 'info',
      JWT_SECRET: 'change-me-to-random-string',
      GUI_USER: 'admin',
      GUI_PASS: 'relay-admin-2026'
    },
    error_file: '/var/log/nastools-relay-error.log',
    out_file: '/var/log/nastools-relay-out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    merge_logs: true
  }]
};
