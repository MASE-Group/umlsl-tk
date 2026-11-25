<script setup lang="ts">
defineProps<{ step: number }>()
</script>
<template>
<svg viewBox="0 0 900 215" role="img" aria-label="Claim space; withdraw on conflict; otherwise reserve, manoeuvre and release">
<defs><marker id="claim-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0L10,5L0,10Z" fill="#445e6f" /></marker></defs>
<g font-family="Helvetica Neue, Arial, sans-serif" text-anchor="middle" fill="#002d4c">
<rect x="10" y="78" width="180" height="65" rx="3" fill="#edf1f3" stroke="#a8b9c4"/><text x="100" y="117" style="font-size:25px" font-weight="700">Claim</text>
<path d="M195,110H310" stroke="#445e6f" stroke-width="2" marker-end="url(#claim-arrow)"/>
<text x="257" y="91" style="font-size:18px">check</text>
<rect x="320" y="78" width="210" height="65" rx="3" fill="#edf1f3" stroke="#a8b9c4"/><text x="425" y="117" style="font-size:24px">Conflict?</text>
<g v-if="step >= 1"><path d="M425,75V24H100V73" fill="none" stroke="#a22223" stroke-width="2" marker-end="url(#claim-arrow)"/><rect x="180" y="8" width="170" height="30" fill="white"/><text x="265" y="29" style="font-size:20px" fill="#a22223">yes → withdraw</text></g>
<g v-if="step >= 2"><path d="M535,110H675" stroke="#009682" stroke-width="2" marker-end="url(#claim-arrow)"/><text x="603" y="91" style="font-size:18px" fill="#009682">no, after wait</text><rect x="685" y="78" width="205" height="65" rx="3" fill="#d9efec" stroke="#009682"/><text x="787" y="117" style="font-size:25px" font-weight="700">Reserve</text><text x="787" y="183" style="font-size:20px">manoeuvre → release</text></g>
</g></svg>
</template>
