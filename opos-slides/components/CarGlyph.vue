<script setup lang="ts">
/*
 * Top view of a car, for use inside an <svg>. (x, y) is the top-left corner of the
 * bounding box, w the length along the driving direction and h the width. The drawing
 * faces `dir`; the label on the roof always stays upright.
 */
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  x: number
  y: number
  w?: number
  h?: number
  label?: string
  dir?: 'right' | 'left' | 'up' | 'down'
  body?: string
}>(), { w: 40, h: 22, dir: 'right', body: '#002d4c' })

// length L and width W of the car itself; vertical cars swap the box sides
const vertical = computed(() => props.dir === 'up' || props.dir === 'down')
const L = computed(() => (vertical.value ? props.h : props.w))
const W = computed(() => (vertical.value ? props.w : props.h))
const cx = computed(() => props.x + props.w / 2)
const cy = computed(() => props.y + props.h / 2)
const angle = computed(() => ({ right: 0, down: 90, left: 180, up: 270 } as const)[props.dir])
// the car is drawn facing right with its centre at the origin, then rotated into place
const transform = computed(() => `translate(${cx.value} ${cy.value}) rotate(${angle.value})`)

const p = (pts: [number, number][]) => pts.map(([a, b]) => `${a * L.value - L.value / 2},${b * W.value - W.value / 2}`).join(' ')
const front = computed(() => p([[0.6, 0.2], [0.75, 0.12], [0.75, 0.88], [0.6, 0.8]]))
const rear = computed(() => p([[0.12, 0.18], [0.22, 0.24], [0.22, 0.76], [0.12, 0.82]]))
const fontSize = computed(() => Math.min(13, Math.max(9, Math.min(L.value, W.value) * 0.58)))
</script>

<template>
  <g class="car-glyph">
    <g :transform="transform">
      <!-- wheels -->
      <rect v-for="(wx, i) in [0.14, 0.64]" :key="`t${i}`" :x="wx * L - L / 2" :y="-W / 2 - W * 0.03"
            :width="L * 0.2" :height="W * 0.16" rx="1.2" fill="#1d2b36" />
      <rect v-for="(wx, i) in [0.14, 0.64]" :key="`b${i}`" :x="wx * L - L / 2" :y="W / 2 - W * 0.13"
            :width="L * 0.2" :height="W * 0.16" rx="1.2" fill="#1d2b36" />
      <!-- body -->
      <rect :x="-L / 2" :y="-W / 2 + W * 0.06" :width="L" :height="W * 0.88" :rx="W * 0.28" :fill="body" />
      <!-- windscreen and rear window -->
      <polygon :points="front" fill="#c9d6df" />
      <polygon :points="rear" fill="#9fb2bf" />
      <!-- headlights -->
      <rect :x="L / 2 - L * 0.06" :y="-W / 2 + W * 0.14" :width="L * 0.04" :height="W * 0.16" fill="#f4f6f7" />
      <rect :x="L / 2 - L * 0.06" :y="W / 2 - W * 0.3" :width="L * 0.04" :height="W * 0.16" fill="#f4f6f7" />
    </g>
    <!-- label on the roof, between the two windows -->
    <text v-if="label" :x="cx + (dir === 'right' ? -0.08 : dir === 'left' ? 0.08 : 0) * L"
          :y="cy + (dir === 'down' ? -0.08 : dir === 'up' ? 0.08 : 0) * L"
          dy="0.36em" text-anchor="middle" :font-size="fontSize" font-weight="700" fill="#fff"
          style="font-family: var(--kit-font-body)">{{ label }}</text>
  </g>
</template>
