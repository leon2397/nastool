<template>
  <div class="min-h-screen bg-dark flex flex-col">
    <!-- 顶部导航栏 -->
    <header v-if="isAuthenticated" class="bg-panel border-b border-border h-14 flex items-center justify-between px-4">
      <div class="flex items-center gap-4">
        <button @click="sidebarCollapsed = !sidebarCollapsed" class="lg:hidden p-2 hover:bg-border rounded">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <div class="flex items-center gap-2">
          <svg class="w-6 h-6 text-accent" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
          </svg>
          <span class="font-semibold text-lg">NasTools V3.0</span>
        </div>
      </div>
      
      <div class="flex items-center gap-6">
        <div class="flex items-center gap-2 text-sm">
          <span class="text-gray-400">设备:</span>
          <span class="text-accent font-medium">{{ onlineCount }}/{{ totalCount }}</span>
        </div>
        
        <WSStatus :connected="wsConnected" />
        
        <button @click="handleLogout" class="flex items-center gap-2 px-3 py-1.5 hover:bg-border rounded text-sm">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          <span>登出</span>
        </button>
      </div>
    </header>

    <div class="flex flex-1 overflow-hidden">
      <!-- 侧边栏 -->
      <aside v-if="isAuthenticated" 
             :class="[
               'bg-panel border-r border-border transition-all duration-300 overflow-y-auto',
               sidebarCollapsed ? 'w-0 lg:w-64' : 'w-64'
             ]">
        <nav class="p-4 space-y-2">
          <router-link
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="flex items-center gap-3 px-3 py-2 rounded hover:bg-border transition-colors"
            :class="{ 'bg-accent bg-opacity-20 text-accent': $route.path === item.path }"
          >
            <component :is="item.icon" class="w-5 h-5" />
            <span>{{ item.name }}</span>
          </router-link>
        </nav>
      </aside>

      <!-- 主内容区 -->
      <main class="flex-1 overflow-y-auto p-6">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>

    <!-- 通知弹窗 -->
    <Notifications :notifications="notifications" @close="removeNotification" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'
import { useDevicesStore } from './stores/devices'
import WSStatus from './components/WSStatus.vue'
import Notifications from './components/Notifications.vue'

const router = useRouter()
const authStore = useAuthStore()
const devicesStore = useDevicesStore()

const sidebarCollapsed = ref(true)

const isAuthenticated = computed(() => !!authStore.token)
const wsConnected = computed(() => devicesStore.wsConnected)
const notifications = computed(() => devicesStore.notifications)
const onlineCount = computed(() => devicesStore.onlineDevices.length)
const totalCount = computed(() => devicesStore.devices.length)

const navItems = [
  { name: '设备列表', path: '/devices', icon: 'DeviceIcon' },
  { name: '舰队管理', path: '/fleets', icon: 'FleetIcon' },
  { name: '诊断报告', path: '/reports', icon: 'ReportIcon' },
  { name: '部署管理', path: '/deploy', icon: 'DeployIcon' },
  { name: '设置', path: '/settings', icon: 'SettingsIcon' },
]

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}

const removeNotification = (id) => {
  const index = devicesStore.notifications.findIndex(n => n.id === id)
  if (index !== -1) {
    devicesStore.notifications.splice(index, 1)
  }
}

onMounted(() => {
  if (isAuthenticated.value) {
    devicesStore.connectWebSocket(authStore.relayUrl, authStore.token)
    devicesStore.fetchDevices()
  }
})
</script>
