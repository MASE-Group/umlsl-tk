<script setup lang="ts">
/*
 * Critical points CP(V, φ) on one virtual lane, for φ = re(E) ⌢ (ℓ > 2 ∧ free):
 * K(φ) = {2}, chop depth d = 1. Illustrative positions on [b, e] = [0, 12].
 *   step 1: base points   (b, e, endpoints of RE(E) and of the crossing segment)
 *   step 2: offsets       (b + 2, e − 2; b − 2 and e + 2 fall outside (b, e))
 *   step 3: midpoints     (one per open gap between adjacent points)
 *   step 4: try the points as r; r = 1.5 splits so that both operands hold
 * Shapes, not colours, tell the three kinds apart (grey palette only).
 */
import { computed } from 'vue'

const props = withDefaults(defineProps<{ step?: number }>(), { step: 4 })

const X0 = 60, X1 = 560
const px = (v: number) => X0 + (v / 12) * (X1 - X0)
const base = [0, 1.5, 6, 8, 12]
const offs = [2, 10]
const sorted = computed(() => [...new Set([...base, ...offs])].sort((a, b) => a - b))
const mids = computed(() => sorted.value.slice(1).map((v, i) => (v + sorted.value[i]) / 2))
const fmt = (v: number) => (Number.isInteger(v) ? `${v}` : v.toFixed(2).replace(/0$/, ''))
</script>

<template>
  <svg viewBox="0 0 600 236" class="cp" role="img" aria-label="Critical points on an observed space">
    <!-- the lane and what lies on it -->
    <rect :x="X0" y="40" :width="X1 - X0" height="56" fill="#edf1f3" stroke="#a8b9c4" stroke-width="1.5" />
    <rect :x="px(6)" y="40" :width="px(8) - px(6)" height="56" fill="#c7d3db" />
    <text :x="(px(6) + px(8)) / 2" y="73" class="atom">cs</text>
    <rect :x="px(0)" y="50" :width="px(1.5) - px(0)" height="36" fill="#a8b9c4" />
    <rect :x="px(0) + 3" y="58" width="30" height="20" rx="3" fill="#002d4c" />
    <text :x="px(0) + 18" y="73" class="carl">E</text>
    <text :x="px(1.5) + 32" y="31" class="atom">RE(E)</text>
    <line :x1="px(1.5) + 14" :x2="px(1.2)" y1="34" y2="50" stroke="#445e6f" stroke-width="1" />
    <text x="54" y="73" class="lbl" style="text-anchor:end">l</text>

    <!-- axis -->
    <line :x1="X0" :x2="X1" y1="120" y2="120" stroke="#002d4c" stroke-width="1.5" />
    <text :x="px(0)" y="232" class="pt">b</text>
    <text :x="px(12)" y="232" class="pt">e</text>

    <!-- 1 base points: filled circles -->
    <g v-if="step >= 1">
      <g v-for="v in base" :key="`b${v}`">
        <line :x1="px(v)" :x2="px(v)" y1="96" y2="120" stroke="#a8b9c4" stroke-width="1" stroke-dasharray="2 2" />
        <circle :cx="px(v)" cy="120" r="6" fill="#002d4c" />
      </g>
      <text x="10" y="124" class="row">Base</text>
    </g>
    <!-- 2 offsets: open squares, with the distance k = 2 from b and from e -->
    <g v-if="step >= 2">
      <g v-for="v in offs" :key="`o${v}`">
        <rect :x="px(v) - 6" y="140" width="12" height="12" fill="#fff" stroke="#002d4c" stroke-width="2" />
      </g>
      <path :d="`M${px(0)},160 L${px(2)},160`" stroke="#445e6f" stroke-width="1.2" />
      <text :x="(px(0) + px(2)) / 2" y="174" class="k">+2</text>
      <path :d="`M${px(10)},160 L${px(12)},160`" stroke="#445e6f" stroke-width="1.2" />
      <text :x="(px(10) + px(12)) / 2" y="174" class="k">−2</text>
      <text x="10" y="150" class="row">Off</text>
    </g>
    <!-- 3 midpoints: small triangles -->
    <g v-if="step >= 3">
      <path v-for="v in mids" :key="`m${v}`" :d="`M${px(v)},186 l6,10 l-12,0 Z`" fill="#6f8797" />
      <text x="10" y="196" class="row">Mid</text>
    </g>
    <!-- 4 the chop tries the candidates; r = 1.5 is a witness -->
    <g v-if="step >= 4">
      <line :x1="px(1.5)" :x2="px(1.5)" y1="30" y2="210" stroke="#002d4c" stroke-width="2.5" />
      <text :x="px(1.5) + 6" y="216" class="wit">r = 1.5: re(E) on [b, r], ℓ &gt; 2 ∧ free on [r, e]</text>
    </g>
  </svg>
</template>

<style scoped>
.cp { width: 100%; height: auto; font-family: var(--kit-font-body); }
.atom { font-size: 15px; font-style: italic; fill: #002d4c; text-anchor: middle; }
.carl { font-size: 15px; font-weight: 700; fill: #fff; text-anchor: middle; }
.lbl { font-size: 15px; font-style: italic; fill: #445e6f; }
.pt { font-size: 15px; font-style: italic; fill: #445e6f; text-anchor: middle; }
.row { font-size: 15px; font-weight: 700; fill: #445e6f; }
.k { font-size: 15px; fill: #445e6f; text-anchor: middle; }
.wit { font-size: 15px; font-weight: 700; fill: #002d4c; }
</style>
