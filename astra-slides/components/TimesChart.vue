<script setup lang="ts">
/* Source: Toolkit_for_UMLSL.pdf Table 1 and committed timing_uniform.json. All values are milliseconds. */
const cars = [2, 4, 6, 8, 10]
const series = [
  { id: 'F6', note: 'no witness', color: '#002d4c', shape: 'diamond',
    ms: [18187.7, 42407.9, 73669.0, 187160.4, 250334.7] },
  { id: 'F2', note: 'safety property', color: '#445e6f', shape: 'square',
    ms: [34.1, 164.3, 411.2, 1037.6, 1490.9] },
  { id: 'F3', note: 'gap ahead', color: '#6f8797', shape: 'triangle',
    ms: [73.7, 197.1, 305.1, 805.6, 1038.4] },
  { id: 'F1', note: '⟨re(E)⟩', color: '#9aaebb', shape: 'circle',
    ms: [9.2, 19.7, 24.9, 54.7, 66.0] },
]

const W = 470, H = 300
const m = { l: 56, r: 40, t: 28, b: 70 }
const nudge: Record<string, number> = { F2: -7, F3: 8 }
const x = (c: number) => m.l + ((c - 2) / 8) * (W - m.l - m.r)
const lo = Math.log10(2), hi = Math.log10(400000)
const y = (v: number) => m.t + (1 - (Math.log10(v) - lo) / (hi - lo)) * (H - m.t - m.b)
const yTicks = [
  { v: 10, t: '10 ms' }, { v: 100, t: '100 ms' }, { v: 1000, t: '1 s' },
  { v: 10000, t: '10 s' }, { v: 100000, t: '100 s' },
]
const path = (ms: number[]) => ms.map((v, i) => `${i ? 'L' : 'M'}${x(cars[i])},${y(v)}`).join(' ')
function marker(shape: string, cx: number, cy: number) {
  const r = 4.5
  if (shape === 'square') return `M${cx - r},${cy - r}h${2 * r}v${2 * r}h${-2 * r}Z`
  if (shape === 'triangle') return `M${cx},${cy - r - 1}L${cx + r + 1},${cy + r}L${cx - r - 1},${cy + r}Z`
  if (shape === 'diamond') return `M${cx},${cy - r - 1.5}L${cx + r + 1.5},${cy}L${cx},${cy + r + 1.5}L${cx - r - 1.5},${cy}Z`
  return `M${cx - r},${cy}a${r},${r} 0 1,0 ${2 * r},0a${r},${r} 0 1,0 ${-2 * r},0`
}
</script>

<template>
  <svg :viewBox="`0 0 ${W} ${H}`" class="times-chart" role="img"
       aria-label="Median decision time against cars in view, log scale">
    <text x="56" y="14" class="axis">decision time · logarithmic scale</text>
    <!-- recessive grid + y axis (log) -->
    <g v-for="t in yTicks" :key="t.v">
      <line :x1="m.l" :x2="W - m.r" :y1="y(t.v)" :y2="y(t.v)" stroke="#dae1e6" stroke-width="1" />
      <text :x="m.l - 6" :y="y(t.v) + 4" style="text-anchor:end" class="tick">{{ t.t }}</text>
    </g>
    <g v-for="c in cars" :key="c">
      <text :x="x(c)" :y="H - m.b + 15" text-anchor="middle" class="tick">{{ c }}</text>
    </g>
    <text :x="(m.l + W - m.r) / 2" :y="H - m.b + 32" text-anchor="middle" class="axis">cars in the virtual view</text>

    <g v-for="s in series" :key="s.id">
      <path :d="path(s.ms)" fill="none" :stroke="s.color" stroke-width="2" />
      <path v-for="(v, i) in s.ms" :key="i" :d="marker(s.shape, x(cars[i]), y(v))"
            :fill="s.color" stroke="#fff" stroke-width="1.5" />
      <!-- direct label at the line end; text stays in ink colour -->
      <text :x="x(10) + 9" :y="y(s.ms[4]) + 4 + (nudge[s.id] ?? 0)" class="lbl" font-weight="700">{{ s.id }}</text>
    </g>

    <!-- legend: shape + id + description (identity never by grey shade alone) -->
    <g v-for="(s, i) in series" :key="`lg${s.id}`">
      <path :d="marker(s.shape, 64 + (i % 2) * 210, H - 28 + Math.floor(i / 2) * 18)" :fill="s.color" />
      <text :x="74 + (i % 2) * 210" :y="H - 24 + Math.floor(i / 2) * 18" class="lbl">
        <tspan font-weight="700">{{ s.id }}</tspan><tspan class="note" dx="5">{{ s.note }}</tspan>
      </text>
    </g>
  </svg>
</template>

<style scoped>
.times-chart { width: 100%; height: auto; font-family: var(--kit-font-body); }
.tick { font-size: 13px; fill: #445e6f; }
.axis { font-size: 14px; fill: #445e6f; }
.lbl { font-size: 14px; fill: #002d4c; }
.note { font-size: 13px; fill: #445e6f; }
</style>
