<template>
  <div class="flex h-screen items-center justify-center bg-gray-900 px-4">
    <div class="w-full max-w-sm">
      <div class="text-center mb-8">
        <h1 class="text-2xl font-bold text-blue-400">OpenDataManager</h1>
        <p class="text-sm text-gray-400 mt-1">Acceso de administración</p>
      </div>

      <form class="bg-gray-800 rounded-xl p-6 shadow-xl space-y-4" @submit.prevent="onSubmit">
        <div>
          <label for="clave" class="block text-sm font-medium text-gray-300 mb-1">
            Clave de administración
          </label>
          <input
            id="clave"
            ref="inputRef"
            v-model="clave"
            type="password"
            autocomplete="current-password"
            class="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 focus:border-blue-500 focus:outline-none"
            placeholder="••••••••••••••••"
            :disabled="loading"
          />
        </div>

        <p v-if="error" class="text-sm text-red-400">{{ error }}</p>

        <button
          type="submit"
          class="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-medium py-2 rounded transition-colors"
          :disabled="loading || !clave"
        >
          {{ loading ? 'Verificando…' : 'Entrar' }}
        </button>
      </form>

      <p class="text-xs text-gray-600 text-center mt-4">
        La clave es el valor de <code>ODM_ADMIN_TOKEN</code> del servidor.
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuth } from '../composables/useAuth'

const { login } = useAuth()
const clave = ref('')
const error = ref('')
const loading = ref(false)
const inputRef = ref(null)

onMounted(() => inputRef.value?.focus())

async function onSubmit() {
  error.value = ''
  loading.value = true
  try {
    await login(clave.value)
    // Al autenticar, App.vue cambia automáticamente a la aplicación.
  } catch (e) {
    error.value = e.message || 'No se pudo iniciar sesión.'
    clave.value = ''
  } finally {
    loading.value = false
  }
}
</script>
