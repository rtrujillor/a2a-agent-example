<script setup lang="ts">
import { Badge } from '@/components/ui/badge'
import type { SourceType } from '@/types/research'

defineProps<{ type: SourceType }>()

// The label carries the type, so it is never conveyed by color alone.
const labels: Record<SourceType, string> = {
  official: 'Oficial',
  media: 'Medio',
  market: 'Mercado',
  other: 'Otra',
}
</script>

<template>
  <Badge :variant="type">{{ labels[type] }}</Badge>
</template>
