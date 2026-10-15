import { createRouter, createWebHistory, type RouteRecordRaw, type RouterHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'

// Navigate by name ({ name: 'home' }), never by hard-coded paths.
// Home is eager (landing page); every other view is lazy.
export const routes: RouteRecordRaw[] = [
  { path: '/', name: 'home', component: HomeView },
  {
    path: '/:pathMatch(.*)*',
    name: 'notFound',
    component: () => import('@/views/NotFoundView.vue'),
  },
]

export function createAppRouter(history: RouterHistory) {
  return createRouter({ history, routes })
}

export default createAppRouter(createWebHistory(import.meta.env.BASE_URL))
