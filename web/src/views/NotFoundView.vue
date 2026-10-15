<script setup lang="ts"></script>

<template>
  <section class="mx-auto max-w-prose space-y-4">
    <h1 class="font-heading text-3xl font-semibold tracking-tight">Página no encontrada</h1>
    <p class="text-muted-foreground">La dirección que has abierto no existe.</p>
    <RouterLink
      :to="{ name: 'home' }"
      class="font-medium text-primary underline underline-offset-4 hover:text-primary/80"
    >
      Volver al inicio
    </RouterLink>
  </section>
</template>
