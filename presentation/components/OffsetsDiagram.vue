<script setup lang="ts">
/*
 * Length comparisons: offsets are measured from the anchors b and e of the current
 * observed space, by every sum s of up to d constants (with repetition). Example:
 * Constants(φ) = {1, 2}, d = 2, so S_2(φ) = {1, 2, 3, 4}. A split point r chosen at one
 * level is an anchor of the sub-space one level down, where the offsets are computed again.
 * Offsets are drawn as open stars, as in CriticalPoints.vue.
 */
const X0 = 90, X1 = 560
const px = (v: number) => X0 + (v / 14) * (X1 - X0)
const S = [1, 2, 3, 4]
const r = 6

const star = (cx: number, cy: number, R = 7.5, q = 3.2) =>
  Array.from({ length: 10 }, (_, i) => {
    const a = -Math.PI / 2 + (i * Math.PI) / 5
    const d = i % 2 === 0 ? R : q
    return `${(cx + d * Math.cos(a)).toFixed(2)},${(cy + d * Math.sin(a)).toFixed(2)}`
  }).join(' ')
</script>

<template>
  <svg viewBox="0 0 600 200" class="offs" role="img" aria-label="Offsets from the anchors b and e, then from r">
    <!-- level 1: [b, e] with b + s and e − s for every s in S_2 -->
    <text x="10" y="64" class="row">level 1</text>
    <line :x1="px(0)" :x2="px(14)" y1="60" y2="60" stroke="#002d4c" stroke-width="1.5" />
    <circle :cx="px(0)" cy="60" r="6" fill="#002d4c" /><circle :cx="px(14)" cy="60" r="6" fill="#002d4c" />
    <text :x="px(0)" y="40" class="pt">b</text><text :x="px(14)" y="40" class="pt">e</text>
    <polygon v-for="s in S" :key="`b${s}`" :points="star(px(s), 60)" class="off" />
    <polygon v-for="s in S" :key="`e${s}`" :points="star(px(14 - s), 60)" class="off" />
    <text :x="(px(1) + px(4)) / 2" y="88" class="pt">b + s</text>
    <text :x="(px(10) + px(13)) / 2" y="88" class="pt">e − s</text>
    <text :x="(px(1) + px(4)) / 2" y="40" class="k">s = 1, 2, 3, 4</text>
    <text :x="(px(10) + px(13)) / 2" y="40" class="k">s = 4, 3, 2, 1</text>

    <!-- chosen split point r at level 1 -->
    <line :x1="px(r)" :x2="px(r)" y1="46" y2="146" stroke="#002d4c" stroke-width="2.5" />
    <text :x="px(r)" y="40" class="pt">r</text>

    <!-- level 2: sub-space [r, e], with r as a new anchor -->
    <text x="10" y="146" class="row">level 2</text>
    <line :x1="px(r)" :x2="px(14)" y1="142" y2="142" stroke="#002d4c" stroke-width="1.5" />
    <circle :cx="px(r)" cy="142" r="6" fill="#002d4c" /><circle :cx="px(14)" cy="142" r="6" fill="#002d4c" />
    <polygon v-for="s in S" :key="`r${s}`" :points="star(px(r + s), 142)" class="off" />
    <text :x="(px(r + 1) + px(r + 4)) / 2" y="170" class="pt">r + s</text>
    <text x="300" y="194" class="note">r is a new anchor: the offsets are computed again on [r, e]</text>
  </svg>
</template>

<style scoped>
.offs { width: 100%; height: auto; font-family: var(--kit-font-body); }
.row { font-size: 11px; font-weight: 700; fill: #445e6f; }
.pt { font-size: 13px; font-style: italic; fill: #002d4c; text-anchor: middle; }
.k { font-size: 11px; fill: #445e6f; text-anchor: middle; }
.note { font-size: 12px; fill: #445e6f; text-anchor: middle; }
.off { fill: #fff; stroke: #002d4c; stroke-width: 1.7; stroke-linejoin: round; }
</style>
