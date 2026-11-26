<script setup lang="ts">
/*
 * Critical points CP(V, φ) on one virtual lane, for
 *   φ = (re(E) ∧ ℓ ≥ 1) ⌢ (ℓ > 2 ∧ free) ⌢ cs   (chops nest to the left):
 * Constants(φ) = {1, 2}, chop depth d = 2, so the sums of at most two constants are
 * S_2 = {1, 2, 1+1, 1+2, 2+2} = {1, 2, 3, 4}. Illustrative positions on [b, e] = [0, 12].
 *   step 1: base points   (b, e, the end of RE(E), the start of the crossing segment)
 *   step 2: offsets       (b + 1 … b + 4 and e − 4 … e − 1; b − s and e + s fall outside (b, e))
 *   step 3: midpoints     (one per open gap between adjacent points)
 *   step 4: try the points as r; r = 7.5 (outer chop) and r = 5 (inner chop) split the space
 *           so that all three operands hold
 * Shapes tell the three kinds apart: circle, star, triangle. E's colours as in MlslView.
 */
import { computed } from 'vue'

const props = withDefaults(defineProps<{ step?: number }>(), { step: 4 })

const X0 = 60, X1 = 560
const px = (v: number) => X0 + (v / 12) * (X1 - X0)
const resEnd = 5
const csStart = 7.5
const base = [0, resEnd, csStart, 12]
const S = [1, 2, 3, 4]
const offs = [...S, ...S.map(s => 12 - s)]
const sorted = computed(() => [...new Set([...base, ...offs])].sort((a, b) => a - b))
const mids = computed(() => sorted.value.slice(1).map((v, i) => (v + sorted.value[i]) / 2))

// rows, about 2.5 cm apart on the slide
const Y = { base: 120, off: 186, mid: 268 }

// open five-pointed star centred at (cx, cy)
const star = (cx: number, cy: number, R = 8, r = 3.4) =>
  Array.from({ length: 10 }, (_, i) => {
    const a = -Math.PI / 2 + (i * Math.PI) / 5
    const q = i % 2 === 0 ? R : r
    return `${(cx + q * Math.cos(a)).toFixed(2)},${(cy + q * Math.sin(a)).toFixed(2)}`
  }).join(' ')
</script>

<template>
  <svg viewBox="0 0 600 310" class="cp" role="img" aria-label="Critical points on an observed space">
    <!-- the lane and what lies on it -->
    <rect :x="X0" y="40" :width="X1 - X0" height="56" fill="#edf1f3" stroke="#a8b9c4" stroke-width="1.5" />
    <rect :x="px(csStart)" y="40" :width="px(12) - px(csStart)" height="56" fill="#c7d3db" />
    <text :x="(px(csStart) + px(12)) / 2" y="73" class="atom">cs</text>
    <rect :x="px(0)" y="50" :width="px(resEnd) - px(0)" height="36" fill="#86a8c6" />
    <CarGlyph :x="px(0) + 4" :y="57" :w="38" :h="22" label="E" />
    <text :x="(px(0) + px(resEnd)) / 2 + 22" y="73" class="atom">RE(E)</text>
    <text x="54" y="73" class="lbl" style="text-anchor:end">l</text>

    <!-- axis -->
    <line :x1="X0" :x2="X1" :y1="Y.base" :y2="Y.base" stroke="#002d4c" stroke-width="1.5" />
    <text :x="px(0)" :y="Y.base + 24" class="pt">b</text>
    <text :x="px(12)" :y="Y.base + 24" class="pt">e</text>

    <!-- 1 base points: filled circles -->
    <g v-if="step >= 1">
      <g v-for="v in base" :key="`b${v}`">
        <line :x1="px(v)" :x2="px(v)" y1="96" :y2="Y.base" stroke="#a8b9c4" stroke-width="1" stroke-dasharray="2 2" />
        <circle :cx="px(v)" :cy="Y.base" r="6" fill="#002d4c" />
      </g>
      <text x="14" :y="Y.base + 4" class="row">Base</text>
    </g>
    <!-- 2 offsets: open stars at b + s and e − s for every s in S_2 = {1, 2, 3, 4} -->
    <g v-if="step >= 2">
      <polygon v-for="v in offs" :key="`o${v}`" :points="star(px(v), Y.off)"
               fill="#fff" stroke="#002d4c" stroke-width="1.8" stroke-linejoin="round" />
      <text v-for="s in S" :key="`kb${s}`" :x="px(s)" :y="Y.off + 24" class="k">+{{ s }}</text>
      <text v-for="s in S" :key="`ke${s}`" :x="px(12 - s)" :y="Y.off + 24" class="k">−{{ s }}</text>
      <text :x="(px(1) + px(4)) / 2" :y="Y.off + 44" class="k">s ∈ {1, 2, 1+1, 1+2, 2+2}</text>
      <text x="14" :y="Y.off + 4" class="row">Off</text>
    </g>
    <!-- 3 midpoints: small triangles -->
    <g v-if="step >= 3">
      <path v-for="v in mids" :key="`m${v}`" :d="`M${px(v)},${Y.mid - 6} l6,11 l-12,0 Z`" fill="#6f8797" />
      <text x="14" :y="Y.mid + 4" class="row">Mid</text>
    </g>
    <!-- 4 the chops try the candidates; r = 7.5 and r = 5 are witnesses -->
    <g v-if="step >= 4">
      <line v-for="r in [resEnd, csStart]" :key="`r${r}`" :x1="px(r)" :x2="px(r)" y1="30" y2="286" stroke="#002d4c" stroke-width="2.5" />
      <text :x="(px(0) + px(resEnd)) / 2" y="302" class="wit">re(E) ∧ ℓ ≥ 1</text>
      <text :x="(px(resEnd) + px(csStart)) / 2" y="302" class="wit">ℓ &gt; 2 ∧ free</text>
      <text :x="(px(csStart) + px(12)) / 2" y="302" class="wit">cs</text>
    </g>
  </svg>
</template>

<style scoped>
.cp { width: 100%; height: auto; font-family: var(--kit-font-body); }
.atom { font-size: 13px; font-style: italic; fill: #002d4c; text-anchor: middle; }
.lbl { font-size: 13px; font-style: italic; fill: #445e6f; }
.pt { font-size: 13px; font-style: italic; fill: #445e6f; text-anchor: middle; }
.row { font-size: 11px; font-weight: 700; fill: #445e6f; }
.k { font-size: 11px; fill: #445e6f; text-anchor: middle; }
.wit { font-size: 12px; font-weight: 700; fill: #002d4c; text-anchor: middle; }
</style>
