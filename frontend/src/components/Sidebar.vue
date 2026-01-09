<template>
  <div class="w-64 bg-gray-800 border-r border-gray-700 flex flex-col">
    <div class="p-6 border-b border-gray-700">
      <h1 class="text-xl font-bold text-blue-400">OpenDataManager</h1>
      <p class="text-xs text-gray-400 mt-1">Metadata-driven Backend</p>
    </div>

    <nav class="flex-1 p-4 space-y-2">
      <router-link
        to="/"
        class="nav-item"
        :class="{ 'active': $route.path === '/' }"
      >
        <span class="text-lg mr-3">📊</span>
        Dashboard
      </router-link>

      <router-link
        to="/resources"
        class="nav-item"
        :class="{ 'active': $route.path.startsWith('/resources') }"
      >
        <span class="text-lg mr-3">🔌</span>
        Resources
      </router-link>

      <router-link
        to="/applications"
        class="nav-item"
        :class="{ 'active': $route.path === '/applications' }"
      >
        <span class="text-lg mr-3">📦</span>
        Applications
      </router-link>
    </nav>

    <div class="p-4 border-t border-gray-700 text-xs text-gray-500">
      <p>Backend: localhost:8040</p>
      <p class="mt-1">Vue 3 + Vite + Tailwind</p>
    </div>
  </div>
</template>

<style scoped>
.nav-item {
  @apply flex items-center px-4 py-3 rounded-lg text-gray-300 hover:bg-gray-700 hover:text-white transition-colors;
}

.nav-item.active {
  @apply bg-gray-700 text-white font-medium;
}
</style>
