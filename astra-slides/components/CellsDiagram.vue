<script setup lang="ts">
/*
 * Completeness, length-free case: base points cut [b, e] into cells
 * {p0}, (p0, p1), {p1}, ..., {pn}. Every RE / CL / CS interval either contains a cell
 * or misses it, so a witness s can move to the representative of its cell (the midpoint).
 */
const X0 = 70, X1 = 530
const p = [0, 3, 7, 10]
const px = (v: number) => X0 + (v / 10) * (X1 - X0)
</script>

<template>
  <svg viewBox="0 0 600 200" class="cells" role="img" aria-label="Cells between base points">
    <!-- an atom's interval: changes membership only at base points -->
    <rect :x="px(3)" y="26" :width="px(7) - px(3)" height="22" fill="#a8b9c4" />
    <text :x="(px(3) + px(7)) / 2" y="42" class="atom">RE(C)</text>

    <!-- open cells -->
    <g v-for="i in 3" :key="i">
      <rect :x="px(p[i - 1]) + 7" y="76" :width="px(p[i]) - px(p[i - 1]) - 14" height="20"
            fill="#edf1f3" stroke="#a8b9c4" stroke-width="1.2" />
      <text :x="(px(p[i - 1]) + px(p[i])) / 2" y="118" class="cell">(p{{ i - 1 }}, p{{ i }})</text>
    </g>
    <line :x1="X0" :x2="X1" y1="86" y2="86" stroke="#002d4c" stroke-width="1.5" />
    <!-- singleton cells = base points -->
    <g v-for="(v, i) in p" :key="`p${i}`">
      <circle :cx="px(v)" cy="86" r="6" fill="#002d4c" />
      <text :x="px(v)" y="70" class="cell">p{{ i }}</text>
    </g>

    <!-- witness s and its representative m -->
    <text :x="px(4.1)" y="92" class="x">×</text>
    <path :d="`M${px(5)},95 l6,10 l-12,0 Z`" fill="#6f8797" />
    <text :x="px(4.1)" y="72" class="lbl">s</text>
    <text :x="px(5)" y="72" class="lbl">m</text>
    <path :d="`M${px(4.1) + 4},58 C${px(4.1) + 14},46 ${px(5) - 14},46 ${px(5) - 3},58`" fill="none"
          stroke="#445e6f" stroke-width="1.5" marker-end="url(#ca)" />
    <text x="300" y="150" class="note">m is the midpoint of (p1, p2), the representative of the cell of s.</text>
    <text x="300" y="170" class="note">s and m lie in the same cell, so m is a witness too.</text>
    <defs>
      <marker id="ca" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
        <path d="M0,0L10,5L0,10Z" fill="#445e6f" />
      </marker>
    </defs>
  </svg>
</template>

<style scoped>
.cells { width: 100%; height: auto; font-family: var(--kit-font-body); }
.atom { font-size: 15px; font-style: italic; fill: #002d4c; text-anchor: middle; }
.cell { font-size: 15px; font-style: italic; fill: #445e6f; text-anchor: middle; }
.x { font-size: 20px; font-weight: 700; fill: #002d4c; text-anchor: middle; }
.lbl { font-size: 15px; font-style: italic; fill: #002d4c; text-anchor: middle; }
.note { font-size: 15px; fill: #445e6f; text-anchor: middle; }
</style>
