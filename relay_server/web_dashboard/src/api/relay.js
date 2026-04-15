import client from './client'

export const relayApi = {
  getStatus: () => 
    client.get('/relay/status'),

  getMetrics: () => 
    client.get('/relay/metrics'),

  getHealth: () => 
    client.get('/relay/health'),

  restart: () => 
    client.post('/relay/restart')
}
