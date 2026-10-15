<script setup lang="ts">
import ResearchRequestForm from '@/components/ResearchRequestForm.vue'
</script>

<template>
  <section class="mx-auto max-w-prose space-y-6">
    <h1 class="font-heading text-3xl font-semibold tracking-tight">
      Acceso a la vivienda en España
    </h1>

    <p class="leading-relaxed text-muted-foreground">
      Un agente de investigación que explica el acceso a la vivienda en España con datos
      actuales y fuentes verificables, desde el conjunto del país hasta comunidades
      autónomas, provincias y municipios.
    </p>

    <div class="space-y-2">
      <h2 class="font-heading text-xl font-semibold">Qué investiga</h2>
      <ul class="list-disc space-y-1 ps-6">
        <li>Precios de compra y alquiler, y su relación con los salarios.</li>
        <li>Oferta, demanda y vivienda pública.</li>
        <li>Derechos de las personas inquilinas.</li>
        <li>Turismo y alquiler de corta duración.</li>
        <li>Legislación y políticas públicas.</li>
        <li>Noticias y movimientos sociales.</li>
      </ul>
    </div>

    <div class="space-y-2">
      <h2 class="font-heading text-xl font-semibold">Qué no ofrece</h2>
      <ul class="list-disc space-y-1 ps-6">
        <li>Asesoramiento jurídico o financiero personalizado.</li>
        <li>Tasaciones de inmuebles.</li>
        <li>Recomendaciones de inversión.</li>
        <li>Previsiones sin respaldo en datos.</li>
      </ul>
    </div>

    <ResearchRequestForm />
  </section>
</template>
