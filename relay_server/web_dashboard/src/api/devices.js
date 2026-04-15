import client from './client'

export const devicesApi = {
  getAll: () => 
    client.get('/devices'),

  getById: (id) => 
    client.get(`/devices/${id}`),

  create: (data) => 
    client.post('/devices', data),

  update: (id, data) => 
    client.put(`/devices/${id}`, data),

  delete: (id) => 
    client.delete(`/devices/${id}`),

  register: (agentKey) => 
    client.post('/devices/register', { agentKey }),

  getByFleet: (fleetId) => 
    client.get(`/devices/fleet/${fleetId}`)
}
