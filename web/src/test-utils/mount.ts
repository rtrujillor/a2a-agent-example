import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory } from 'vue-router'
import type { Component } from 'vue'
import { createAppRouter } from '@/router'

// Mounts a component with the app's plugins and fresh state per call:
// a new Pinia and a memory-history router at `route` (default '/').
export async function mountWithPlugins(component: Component, { route = '/' } = {}) {
  const pinia = createPinia()
  const router = createAppRouter(createMemoryHistory())
  await router.push(route)
  await router.isReady()
  const wrapper = mount(component, { global: { plugins: [pinia, router] } })
  return { wrapper, router, pinia }
}
