<script setup lang="ts"></script>

<template>
  <div class="flex min-h-screen flex-col">
    <header class="border-b bg-background">
      <div class="mx-auto flex max-w-5xl items-center px-4 py-3">
        <RouterLink :to="{ name: 'home' }" class="font-heading font-semibold hover:text-primary/80">
          Acceso a la vivienda en España
        </RouterLink>
      </div>
    </header>
    <main class="mx-auto w-full max-w-5xl flex-1 p-4">
      <RouterView />
    </main>
  </div>
</template>
