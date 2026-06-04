<template>
  <div class="fixed inset-0 z-[10000] flex items-center justify-center bg-black/70 px-4" @click.self="cerrar">
    <div class="w-full max-w-sm">
      <div class="text-center mb-6">
        <h1 class="text-2xl font-bold text-blue-400">OpenDataManager</h1>
        <p class="text-sm text-gray-400 mt-1">Iniciar sesión</p>
      </div>

      <form class="bg-gray-800 rounded-xl p-6 shadow-xl space-y-4" @submit.prevent="onSubmit">
        <div>
          <label for="usuario" class="block text-sm font-medium text-gray-300 mb-1">Usuario</label>
          <input
            id="usuario" ref="inputRef" v-model="username" type="text" autocomplete="username"
            class="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 focus:border-blue-500 focus:outline-none"
            :disabled="loading"
          />
        </div>
        <div>
          <label for="clave" class="block text-sm font-medium text-gray-300 mb-1">Contraseña</label>
          <input
            id="clave" v-model="password" type="password" autocomplete="current-password"
            class="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 focus:border-blue-500 focus:outline-none"
            :disabled="loading"
          />
        </div>

        <p v-if="error" class="text-sm text-red-400">{{ error }}</p>

        <button
          type="submit"
          class="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-medium py-2 rounded transition-colors"
          :disabled="loading || !username || !password"
        >
          {{ loading ? 'Verificando…' : 'Entrar' }}
        </button>

        <button type="button" class="w-full text-xs text-gray-400 hover:text-gray-200 py-1" @click="cerrar">
          Seguir como invitado (solo lectura)
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuth } from '../composables/useAuth'

const { login, mostrarLogin } = useAuth()
const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const inputRef = ref(null)

onMounted(() => inputRef.value?.focus())

function cerrar() {
  mostrarLogin.value = false
}

async function onSubmit() {
  error.value = ''
  loading.value = true
  try {
    await login(username.value, password.value)
  } catch (e) {
    error.value = e.message || 'No se pudo iniciar sesión.'
    password.value = ''
  } finally {
    loading.value = false
  }
}
</script>
