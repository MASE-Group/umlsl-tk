<script setup lang="ts">
/*
 * Urban traffic model: a horizontal road (one lane to the left, two to the right) crosses
 * a vertical road (one lane down, two up), which gives the crossing segments c0..c8.
 * D holds a crossing reservation (its whole path plus its own length beyond the
 * crossing). E's reservation ends before the crossing; E's virtual view runs through it.
 */
const H = { top: 110, lanes: 3 }      // horizontal road: lanes from y = 110, 40 px each
const V = { left: 290, lanes: 3 }     // vertical road: lanes from x = 290, 40 px each
const LW = 40
// the same blues as in MlslView: E darkest; res = a car's reservation
const P = {
  E: { car: '#002d4c', res: '#86a8c6' },
  D: { car: '#3a7fc1', res: '#b4d3f0' },
}
const cells = Array.from({ length: 9 }, (_, i) => ({
  name: `c${i}`,
  x: V.left + (i % 3) * LW,
  y: H.top + Math.floor(i / 3) * LW,
}))
</script>

<template>
  <svg viewBox="0 0 600 330" class="urban" role="img" aria-label="Intersection with lane and crossing segments">
    <!-- roads -->
    <rect x="10" :y="H.top" width="580" :height="H.lanes * LW" fill="#dae1e6" />
    <rect :x="V.left" y="10" :width="V.lanes * LW" height="310" fill="#dae1e6" />

    <!-- lane markings outside the crossing: solid between the two directions, dashed between lanes of one direction -->
    <line x1="10" :x2="V.left" :y1="H.top + LW" :y2="H.top + LW" class="sep" />
    <line :x1="V.left + 3 * LW" x2="590" :y1="H.top + LW" :y2="H.top + LW" class="sep" />
    <line x1="10" :x2="V.left" :y1="H.top + 2 * LW" :y2="H.top + 2 * LW" class="mid" />
    <line :x1="V.left + 3 * LW" x2="590" :y1="H.top + 2 * LW" :y2="H.top + 2 * LW" class="mid" />
    <line :x1="V.left + LW" :x2="V.left + LW" y1="10" :y2="H.top" class="sep" />
    <line :x1="V.left + LW" :x2="V.left + LW" :y1="H.top + 3 * LW" y2="320" class="sep" />
    <line :x1="V.left + 2 * LW" :x2="V.left + 2 * LW" y1="10" :y2="H.top" class="mid" />
    <line :x1="V.left + 2 * LW" :x2="V.left + 2 * LW" :y1="H.top + 3 * LW" y2="320" class="mid" />

    <!-- crossing segments -->
    <g class="cs">
      <rect v-for="c in cells" :key="c.name" :x="c.x" :y="c.y" :width="LW" :height="LW" />
    </g>

    <!-- D comes down the left lane of the vertical road and turns right: it reserves its
         path through the crossing plus its own length beyond it -->
    <path :d="`M${V.left + 2},28 L${V.left + LW - 2},28 L${V.left + LW - 2},${H.top + LW - 2} L246,${H.top + LW - 2} L246,${H.top + 2} L${V.left + 2},${H.top + 2} Z`" class="res" :fill="P.D.res" />
    <CarGlyph :x="V.left + 7" :y="32" :w="26" :h="42" dir="down" label="D" :body="P.D.car" />
    <text x="262" y="100" class="atom">re(D)</text>

    <!-- E on the lower right-bound lane: its reservation ends before the crossing -->
    <rect x="110" :y="H.top + 2 * LW + 3" width="110" :height="LW - 6" class="res" :fill="P.E.res" />
    <CarGlyph :x="113" :y="H.top + 2 * LW + 9" :w="42" :h="22" label="E" :body="P.E.car" />
    <text x="190" :y="H.top + 2 * LW + 25" class="atom">re(E)</text>
    <!-- the space between E's reservation and the crossing -->
    <line x1="220" :x2="V.left" y1="246" y2="246" stroke="#445e6f" stroke-width="1.2" />
    <line x1="220" x2="220" y1="240" y2="252" stroke="#445e6f" stroke-width="1.2" />
    <line :x1="V.left" :x2="V.left" y1="240" y2="252" stroke="#445e6f" stroke-width="1.2" />
    <text :x="(220 + V.left) / 2" y="266" class="note">free</text>

    <!-- E's virtual view through the crossing -->
    <rect x="50" :y="H.top - 4" width="420" :height="H.lanes * LW + 8" fill="none" stroke="#002d4c" stroke-width="2" stroke-dasharray="7 5" />
    <text x="54" y="100" class="view">V(E)</text>

    <!-- crossing segment names on top, white with a dark outline so they read on any fill -->
    <text v-for="c in cells" :key="`n${c.name}`" :x="c.x + LW / 2" :y="c.y + LW / 2 + 4" class="csname">{{ c.name }}</text>

    <text x="20" y="300" class="note" style="text-anchor:start">c0 … c8: crossing segments</text>
  </svg>
</template>

<style scoped>
.urban { width: 100%; height: auto; font-family: var(--kit-font-body); }
.mid { stroke: #fff; stroke-width: 2; stroke-dasharray: 12 8; }
.sep { stroke: #fff; stroke-width: 2.5; }
.cs rect { fill: #8da1ae; stroke: #fff; stroke-width: 1; stroke-dasharray: 3 3; }
.csname {
  font-size: 12.5px; font-weight: 700; fill: #fff; text-anchor: middle;
  stroke: #445e6f; stroke-width: 2.6px; paint-order: stroke; stroke-linejoin: round;
}
.res { opacity: 0.92; }
.atom { font-size: 13px; font-style: italic; fill: #002d4c; text-anchor: middle; }
.note { font-size: 12px; fill: #445e6f; text-anchor: middle; }
.view { font-size: 12px; font-weight: 700; fill: #002d4c; }
</style>
