<script setup lang="ts">
import { ref } from 'vue'
import {
  BanIcon,
  BuildingIcon,
  CoinsIcon,
  GavelIcon,
  KeyRoundIcon,
  MegaphoneIcon,
  PlaneIcon,
  SearchIcon,
} from '@lucide/vue'
import ExampleQuestions from '@/components/ExampleQuestions.vue'
import ResearchRequestForm from '@/components/ResearchRequestForm.vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const form = ref<InstanceType<typeof ResearchRequestForm>>()

const researches = [
  { icon: CoinsIcon, text: 'Precios de compra y alquiler, y su relación con los salarios.' },
  { icon: BuildingIcon, text: 'Oferta, demanda y vivienda pública.' },
  { icon: KeyRoundIcon, text: 'Derechos de las personas inquilinas.' },
  { icon: PlaneIcon, text: 'Turismo y alquiler de corta duración.' },
  { icon: GavelIcon, text: 'Legislación y políticas públicas.' },
  { icon: MegaphoneIcon, text: 'Noticias y movimientos sociales.' },
]

const exclusions = [
  'Asesoramiento jurídico o financiero personalizado.',
  'Tasaciones de inmuebles.',
  'Recomendaciones de inversión.',
  'Previsiones sin respaldo en datos.',
]
</script>

<template>
  <div class="flex flex-col gap-16">
    <section class="relative mx-auto flex w-full max-w-2xl flex-col gap-8">
      <div aria-hidden="true" class="absolute inset-x-0 -top-16 -z-10 h-80 bg-paper-grid" />

      <div
        class="flex flex-col gap-3 text-center motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:duration-500"
      >
        <h1 class="font-heading text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
          Problema de acceso a la vivienda en España
        </h1>
        <p class="text-lg text-pretty text-muted-foreground">
          Un agente de investigación que explica o trata de buscar referecias sobre el problema el acceso a la vivienda con datos actuales y
          fuentes verificables, del conjunto del país a cada municipio.
        </p>
      </div>

      <div
        class="flex flex-col gap-6 motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:delay-100 motion-safe:duration-500 motion-safe:fill-mode-both"
      >
        <ResearchRequestForm ref="form" />
        <ExampleQuestions @applied="form?.focus()" />
      </div>
    </section>

    <section
      aria-label="Alcance"
      class="grid gap-4 md:grid-cols-2 motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:delay-200 motion-safe:duration-500 motion-safe:fill-mode-both"
    >
      <Card>
        <CardHeader>
          <CardTitle>
            <h2 class="flex items-center gap-2 text-xl">
              <SearchIcon class="size-5 text-primary" aria-hidden="true" />
              Qué investiga
            </h2>
          </CardTitle>
          <CardDescription>
            En España, sus comunidades autónomas, provincias y municipios.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ul class="flex flex-col gap-3">
            <li v-for="item in researches" :key="item.text" class="flex items-start gap-3">
              <component
                :is="item.icon"
                class="mt-0.5 size-4 shrink-0 text-muted-foreground"
                aria-hidden="true"
              />
              <span>{{ item.text }}</span>
            </li>
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>
            <h2 class="flex items-center gap-2 text-xl">
              <BanIcon class="size-5 text-muted-foreground" aria-hidden="true" />
              Qué no ofrece
            </h2>
          </CardTitle>
          <CardDescription> Explica la evidencia; no sustituye a un profesional. </CardDescription>
        </CardHeader>
        <CardContent>
          <ul class="flex flex-col gap-3">
            <li v-for="item in exclusions" :key="item" class="flex items-start gap-3">
              <span
                class="mt-2 size-1.5 shrink-0 rounded-full bg-muted-foreground"
                aria-hidden="true"
              />
              <span>{{ item }}</span>
            </li>
          </ul>
        </CardContent>
      </Card>
    </section>
  </div>
</template>
