import client from './client'

export const commandsApi = {
  send: (deviceId, command) => 
    client.post(`/devices/${deviceId}/commands`, { command }),

  getHistory: (deviceId, params = {}) => 
    client.get(`/devices/${deviceId}/commands/history`, { params }),

  cancel: (deviceId, commandId) => 
    client.post(`/devices/${deviceId}/commands/${commandId}/cancel`)
}
