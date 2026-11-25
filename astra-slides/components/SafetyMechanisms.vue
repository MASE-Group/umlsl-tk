<script setup lang="ts">
/*
 * The two ways UMLSL-Sim uses the safe controller during RL training.
 * Green = action the safe controller accepts, red = action it rejects.
 */
defineProps<{ step: number }>()
const actions = [1, 1, 0, 1, 1, 0, 0, 1, 1]   // 1 = safe, 0 = unsafe (illustration)
</script>

<template>
  <svg viewBox="0 0 600 150" class="sm" role="img" aria-label="Reward shaping versus action masking">
    <!-- reward shaping -->
    <text x="140" y="16" class="ttl">PPO + safety-aware reward</text>
    <g v-for="(a, i) in actions" :key="`r${i}`">
      <rect :x="20 + i * 27" y="34" width="22" height="22" rx="2" :class="a ? 'ok' : 'bad'" />
      <text v-if="!a" :x="31 + i * 27" y="78" class="pen">−</text>
    </g>
    <text x="140" y="104" class="cap">all actions reachable</text>
    <text x="140" y="122" class="cap">penalty after an unsafe step</text>

    <!-- shield -->
    <g v-if="step >= 1">
    <text x="460" y="16" class="ttl">MaskablePPO + shield</text>
    <g v-for="(a, i) in actions" :key="`s${i}`">
      <rect v-if="a" :x="340 + i * 27" y="34" width="22" height="22" rx="2" class="ok" />
      <g v-else>
        <rect :x="340 + i * 27" y="34" width="22" height="22" rx="2" class="masked" />
        <path :d="`M${343 + i * 27},37 l16,16 M${359 + i * 27},37 l-16,16`" stroke="#a22223" stroke-width="2" />
      </g>
    </g>
    <text x="460" y="104" class="cap">unsafe actions masked</text>
    <text x="460" y="122" class="cap">before the agent acts</text>

    </g>
    <line x1="300" x2="300" y1="6" y2="140" stroke="#dae1e6" stroke-width="1.5" />
  </svg>
</template>

<style scoped>
.sm { width: 100%; height: auto; font-family: var(--kit-font-body); }
.ok { fill: #009682; }
.bad { fill: #a22223; }
.masked { fill: #fff; stroke: #a22223; stroke-width: 1.5; stroke-dasharray: 3 2; }
.pen { font-size: 18px; font-weight: 700; fill: #a22223; text-anchor: middle; }
.ttl { font-size: 13.5px; font-weight: 700; fill: #002d4c; text-anchor: middle; }
.cap { font-size: 12.5px; fill: #445e6f; text-anchor: middle; }
</style>
