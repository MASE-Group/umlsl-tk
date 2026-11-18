<script setup lang="ts">
/*
 * Length comparisons: offsets are measured from the anchors b and e of the current
 * observed space. A split point s chosen at one level is an anchor of the sub-space
 * one level down, where the offsets are computed again.
 */
const X0 = 90, X1 = 560
const px = (v: number) => X0 + (v / 12) * (X1 - X0)
</script>

<template>
  <svg viewBox="0 0 600 190" class="offs" role="img" aria-label="Offsets from the anchors b and e, then from s">
    <defs>
      <marker id="oa" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M0,0L10,5L0,10Z" fill="#445e6f" />
      </marker>
    </defs>

    <!-- level 1 -->
    <text x="10" y="56" class="row">level 1</text>
    <line :x1="px(0)" :x2="px(12)" y1="52" y2="52" stroke="#002d4c" stroke-width="1.5" />
    <circle :cx="px(0)" cy="52" r="6" fill="#002d4c" /><circle :cx="px(12)" cy="52" r="6" fill="#002d4c" />
    <text :x="px(0)" y="32" class="pt">b</text><text :x="px(12)" y="32" class="pt">e</text>
    <rect :x="px(3) - 6" y="46" width="12" height="12" fill="#fff" stroke="#002d4c" stroke-width="2" />
    <rect :x="px(9) - 6" y="46" width="12" height="12" fill="#fff" stroke="#002d4c" stroke-width="2" />
    <text :x="px(3)" y="32" class="pt">b + k</text>
    <text :x="px(9)" y="32" class="pt">e − k</text>

    <!-- chosen split point s at level 1 -->
    <line :x1="px(5)" :x2="px(5)" y1="40" y2="128" stroke="#002d4c" stroke-width="2.5" />
    <text :x="px(5)" y="32" class="pt">s</text>

    <!-- level 2: sub-space [s, e] -->
    <text x="10" y="132" class="row">level 2</text>
    <line :x1="px(5)" :x2="px(12)" y1="128" y2="128" stroke="#002d4c" stroke-width="1.5" />
    <circle :cx="px(5)" cy="128" r="6" fill="#002d4c" /><circle :cx="px(12)" cy="128" r="6" fill="#002d4c" />
    <rect :x="px(8) - 6" y="122" width="12" height="12" fill="#fff" stroke="#002d4c" stroke-width="2" />
    <text :x="px(8)" y="154" class="pt">s + k</text>
    <line :x1="px(5) + 8" :x2="px(8) - 9" y1="142" y2="142" stroke="#445e6f" stroke-width="1.2"
          marker-start="url(#oa)" marker-end="url(#oa)" />
    <text x="300" y="182" class="note">s is a new anchor: offsets are computed again on [s, e]</text>
  </svg>
</template>

<style scoped>
.offs { width: 100%; height: auto; font-family: var(--kit-font-body); }
.row { font-size: 11px; font-weight: 700; fill: #445e6f; }
.pt { font-size: 13px; font-style: italic; fill: #002d4c; text-anchor: middle; }
.note { font-size: 12px; fill: #445e6f; text-anchor: middle; }
</style>
