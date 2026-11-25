<script setup lang="ts">
/*
 * The crossing claim as a lease (UMLSL-Sim, IntersectionState): illustrative timeline.
 * A claims first (frame 0) and moves, renewing its lease each frame. A stalls at frame 5.
 * After 4 frames without progress (frame 9) its claim is reordered behind B, which claimed
 * at frame 2 and was waiting; B now enters. After 12 frames without progress (frame 17)
 * A's claim is withdrawn (wd cc(A)); A claims again later, at the back of the queue.
 * Greys only: nothing here is safe or unsafe.
 */
const X0 = 96, X1 = 860
const F = 20
const fx = (f: number) => X0 + (f / F) * (X1 - X0)
const RA = 52, RB = 112, BH = 24
</script>

<template>
  <svg viewBox="0 0 880 196" class="lease" role="img" aria-label="Timeline of a crossing claim held as a lease">
    <defs>
      <pattern id="lt-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width="6" height="6" fill="#edf1f3" />
        <line x1="0" y1="0" x2="0" y2="6" stroke="#c7d3db" stroke-width="2.5" />
      </pattern>
    </defs>

    <!-- row labels -->
    <CarGlyph :x="20" :y="RA + 2" :w="38" :h="20" label="A" />
    <CarGlyph :x="20" :y="RB + 2" :w="38" :h="20" label="B" />

    <!-- A: moves and renews, then stalls -->
    <rect :x="fx(0)" :y="RA" :width="fx(5) - fx(0)" :height="BH" class="move" />
    <text :x="(fx(0) + fx(5)) / 2" :y="RA + 16" class="in">moves: renews each frame</text>
    <rect :x="fx(5)" :y="RA" :width="fx(17) - fx(5)" :height="BH" fill="url(#lt-hatch)" class="stall" />
    <text :x="(fx(5) + fx(9)) / 2" :y="RA + 16" class="in">stalled</text>
    <text :x="(fx(9) + fx(17)) / 2" :y="RA + 16" class="in">stalled, behind B</text>
    <text :x="fx(17) + 8" :y="RA + 16" class="in" style="text-anchor:start">claims again later</text>

    <!-- B: claims after A, waits, then enters once A is reordered -->
    <rect :x="fx(2)" :y="RB" :width="fx(9) - fx(2)" :height="BH" fill="url(#lt-hatch)" class="stall" />
    <text :x="(fx(2) + fx(9)) / 2" :y="RB + 16" class="in">claimed, waits: A is first</text>
    <rect :x="fx(9)" :y="RB" :width="fx(13) - fx(9)" :height="BH" class="move" />
    <text :x="(fx(9) + fx(13)) / 2" :y="RB + 16" class="in">enters, crosses</text>

    <!-- events -->
    <g class="ev">
      <line :x1="fx(0)" :x2="fx(0)" :y1="RA - 10" :y2="RA + BH + 4" />
      <line :x1="fx(2)" :x2="fx(2)" :y1="RB - 6" :y2="RB + BH + 4" />
      <line :x1="fx(9)" :x2="fx(9)" :y1="RA - 10" :y2="RB + BH + 4" />
      <line :x1="fx(17)" :x2="fx(17)" :y1="RA - 10" :y2="RA + BH + 4" />
    </g>
    <text :x="fx(0)" :y="RA - 16" class="evl" style="text-anchor:start">cc(A): A claims, first in the order</text>
    <text :x="fx(9)" :y="RA - 16" class="evl">4 frames stalled: reordered</text>
    <text :x="fx(17)" :y="RA - 16" class="evl">12 frames stalled: wd cc(A)</text>
    <text :x="fx(2) - 6" :y="RB + 16" class="evl" style="text-anchor:end">cc(B)</text>

    <!-- axis in frames -->
    <line :x1="X0" :x2="X1" y1="166" y2="166" stroke="#002d4c" stroke-width="1.5" />
    <g v-for="f in F + 1" :key="f">
      <line :x1="fx(f - 1)" :x2="fx(f - 1)" y1="162" y2="170" stroke="#445e6f" stroke-width="1" />
    </g>
    <text v-for="f in [0, 5, 9, 13, 17, 20]" :key="`l${f}`" :x="fx(f)" y="186" class="ax">{{ f }}</text>
    <text :x="X0 - 10" y="186" class="ax" style="text-anchor:end">frame</text>
  </svg>
</template>

<style scoped>
.lease { width: 100%; height: auto; font-family: var(--kit-font-body); }
.move { fill: #a8b9c4; }
.stall { stroke: #a8b9c4; stroke-width: 1; }
.in { font-size: 12px; fill: #002d4c; text-anchor: middle; }
.ev line { stroke: #002d4c; stroke-width: 1.5; stroke-dasharray: 3 2; }
.evl { font-size: 12px; font-weight: 700; fill: #002d4c; text-anchor: middle; }
.ax { font-size: 11px; fill: #445e6f; text-anchor: middle; }
</style>
