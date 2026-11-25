<script setup lang="ts">
/*
 * Inline legend marks for the three kinds of critical points, drawn exactly as in
 * CriticalPoints.vue and OffsetsDiagram.vue: base = filled circle, offset = open star,
 * midpoint = small triangle. The star avoids the box and diamond of modal logic.
 */
defineProps<{ kind: 'base' | 'off' | 'mid' }>()
</script>

<template>
  <svg viewBox="0 0 18 18" class="pmark" aria-hidden="true">
    <circle v-if="kind === 'base'" cx="9" cy="9" r="6" fill="#002d4c" />
    <polygon v-else-if="kind === 'off'"
             points="9,1.2 11.1,6.3 16.6,6.6 12.4,10.2 13.8,15.6 9,12.6 4.2,15.6 5.6,10.2 1.4,6.6 6.9,6.3"
             fill="#fff" stroke="#002d4c" stroke-width="1.6" stroke-linejoin="round" />
    <path v-else d="M9,3 l6,11 l-12,0 Z" fill="#6f8797" />
  </svg>
</template>

<style scoped>
.pmark { display: inline-block; width: 15px; height: 15px; vertical-align: -2px; margin-right: 3px; }
</style>
