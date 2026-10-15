<script setup lang="ts">
import { Button } from '@/components/ui/button'
import { useResearchStore } from '@/stores/research'

const emit = defineEmits<{ applied: [] }>()

const store = useResearchStore()

// Neutral phrasings: each asks what the evidence shows, not for a verdict.
const examples = [
  '¿Cómo han evolucionado los alquileres frente a los salarios en España?',
  '¿Qué dicen los datos sobre los pisos turísticos y el alquiler en Barcelona?',
  '¿Cuánta vivienda pública hay en España en comparación con otros países europeos?',
] as const

// Fills the field without sending; the parent moves focus to it.
function apply(example: string) {
  store.applyExample(example)
  emit('applied')
}
</script>

<template>
  <section aria-labelledby="examples-heading" class="flex flex-col gap-2">
    <h2 id="examples-heading" class="text-sm font-medium text-muted-foreground">
      Prueba con un ejemplo
    </h2>
    <ul class="flex flex-wrap gap-2">
      <li v-for="example in examples" :key="example">
        <Button
          type="button"
          variant="outline"
          size="sm"
          class="h-auto rounded-full py-1.5 text-left whitespace-normal"
          @click="apply(example)"
        >
          {{ example }}
        </Button>
      </li>
    </ul>
  </section>
</template>
