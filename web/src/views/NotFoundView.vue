<script setup lang="ts">
import { MapPinOffIcon } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty'
</script>

<template>
  <Empty>
    <EmptyHeader>
      <EmptyMedia variant="icon">
        <MapPinOffIcon />
      </EmptyMedia>
      <EmptyTitle>
        <h1 class="text-2xl">Página no encontrada</h1>
      </EmptyTitle>
      <EmptyDescription>La dirección que has abierto no existe.</EmptyDescription>
    </EmptyHeader>
    <EmptyContent>
      <Button variant="outline" as-child>
        <RouterLink :to="{ name: 'home' }">Volver al inicio</RouterLink>
      </Button>
    </EmptyContent>
  </Empty>
</template>
