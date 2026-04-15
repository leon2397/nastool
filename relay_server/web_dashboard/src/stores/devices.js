import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { devicesApi } from '../api/devices'
import { commandsApi } from '../api/commands'
import { reportsApi } from '../api/reports'
import { RelayWS } from '../websocket/relay'

export const useDevicesStore = defineStore('devices', () => {
  const devices = ref([])
  const selectedDevice = ref(null)
  const wsConnected = ref(false)
  const notifications = ref([])
  
  let wsClient = null

  // Getters
  const onlineDevices = computed(() => 
    devices.value.filter(d => d.status === 'online')
  )

  const offlineDevices = computed(() => 
    devices.value.filter(d => d.status === 'offline')
  )

  const devicesByFleet = computed(() => {
    const grouped = {}
    devices.value.forEach(device => {
      const fleet = device.fleet || 'default'
      if (!grouped[fleet]) {
        grouped[fleet] = []
      }
      grouped[fleet].push(device)
    })
    return grouped
  })

  // Actions
  const fetchDevices = async () => {
    try {
      const response = await devicesApi.getAll()
      devices.value = response.data
    } catch (error) {
      console.error('获取设备列表失败:', error)
    }
  }

  const fetchDevice = async (id) => {
    try {
      const response = await devicesApi.getById(id)
      selectedDevice.value = response.data
      return response.data
    } catch (error) {
      console.error('获取设备详情失败:', error)
      return null
    }
  }

  const sendCommand = async (id, cmd) => {
    try {
      const response = await commandsApi.send(id, cmd)
      return response.data
    } catch (error) {
      console.error('发送命令失败:', error)
      throw error
    }
  }

  const fetchReports = async (id, params = {}) => {
    try {
      const response = await reportsApi.getByDevice(id, params)
      return response.data
    } catch (error) {
      console.error('获取报告失败:', error)
      return []
    }
  }

  const addNotification = (notification) => {
    const id = Date.now()
    notifications.value.push({
      id,
      ...notification,
      timestamp: new Date().toISOString()
    })
    
    // 自动移除（5秒后）
    setTimeout(() => {
      removeNotification(id)
    }, 5000)
  }

  const removeNotification = (id) => {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index !== -1) {
      notifications.value.splice(index, 1)
    }
  }

  const connectWebSocket = (url, token) => {
    if (wsClient) {
      wsClient.disconnect()
    }

    wsClient = new RelayWS()
    
    wsClient.on('open', () => {
      wsConnected.value = true
      addNotification({ type: 'success', message: 'WebSocket 连接成功' })
    })

    wsClient.on('close', () => {
      wsConnected.value = false
      addNotification({ type: 'warning', message: 'WebSocket 连接已断开' })
    })

    wsClient.on('error', (error) => {
      addNotification({ type: 'error', message: 'WebSocket 连接错误' })
    })

    wsClient.on('report', (data) => {
      // 更新设备列表中的设备状态
      const device = devices.value.find(d => d.id === data.deviceId)
      if (device) {
        Object.assign(device, data)
      }
    })

    wsClient.on('notification', (data) => {
      addNotification(data)
    })

    wsClient.on('heartbeat_ack', () => {
      wsConnected.value = true
    })

    wsClient.connect(url, token)
  }

  const disconnectWebSocket = () => {
    if (wsClient) {
      wsClient.disconnect()
      wsClient = null
      wsConnected.value = false
    }
  }

  return {
    devices,
    selectedDevice,
    wsConnected,
    notifications,
    onlineDevices,
    offlineDevices,
    devicesByFleet,
    fetchDevices,
    fetchDevice,
    sendCommand,
    fetchReports,
    addNotification,
    removeNotification,
    connectWebSocket,
    disconnectWebSocket
  }
})
