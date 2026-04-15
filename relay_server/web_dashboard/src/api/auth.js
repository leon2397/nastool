import client from './client'

export const authApi = {
  login: (username, password) => 
    client.post('/auth/login', { username, password }),

  refresh: () => 
    client.post('/auth/refresh'),

  logout: () => 
    client.post('/auth/logout'),

  me: () => 
    client.get('/auth/me')
}
