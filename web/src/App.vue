<script setup lang="ts">
import { HouseIcon } from '@lucide/vue'
import ThemeToggle from '@/components/ThemeToggle.vue'
</script>

<template>
  <div class="flex min-h-screen flex-col">
    <header
      class="sticky top-0 z-40 border-b bg-background/80 backdrop-blur supports-backdrop-filter:bg-background/60"
    >
      <div class="mx-auto flex h-14 max-w-5xl items-center justify-between gap-4 px-4">
        <RouterLink
          :to="{ name: 'home' }"
          class="flex items-center gap-2 rounded-md font-heading text-lg font-semibold tracking-tight hover:text-primary focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
        >
          <span
            class="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground"
            aria-hidden="true"
          >
            <HouseIcon class="size-4" />
          </span>
          Acceso a la vivienda en España
        </RouterLink>
        <ThemeToggle />
      </div>
    </header>
    <main class="mx-auto w-full max-w-5xl flex-1 px-4 py-10 sm:py-16">
      <RouterView />
    </main>
  </div>
</template>
