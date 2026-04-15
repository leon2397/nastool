import client from './client'

export const reportsApi = {
  getByDevice: (deviceId, params = {}) => 
    client.get(`/devices/${deviceId}/reports`, { params }),

  getById: (deviceId, reportId) => 
    client.get(`/devices/${deviceId}/reports/${reportId}`),

  getLatest: (deviceId) => 
    client.get(`/devices/${deviceId}/reports/latest`),

  export: (deviceId, reportId, format = 'json') => 
    client.get(`/devices/${deviceId}/reports/${reportId}/export`, {
      params: { format },
      responseType: 'blob'
    })
}
