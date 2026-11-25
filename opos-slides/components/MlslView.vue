<script setup lang="ts">
/*
 * Highway model of MLSL: lanes (discrete), positions (continuous), reservations
 * (safety envelope), a claim (dashed) and the virtual view V(E) of the ego car E.
 * Each car has its own shade of blue; its reservation and claim use a light tint of it.
 * No green or red: nothing here is safe or unsafe yet.
 */
defineProps<{ bare?: boolean }>()   // bare: only the road, the cars and their space

const lanes = [0, 1, 2]
const laneY = (l: number) => 168 - l * 46   // lane 0 at the bottom
const laneH = 40

// one shade of blue per car (E, the ego car, darkest); res = its reservation
const P = {
  E: { car: '#002d4c', res: '#86a8c6' },
  B: { car: '#1d5a8c', res: '#a3c1de' },
  C: { car: '#3a7fc1', res: '#b4d3f0' },
  A: { car: '#6aa6d6', res: '#c9e1f5' },
}
</script>

<template>
  <svg :viewBox="bare ? '6 66 588 156' : '0 0 600 254'" class="mlsl" role="img" aria-label="Highway with reservations, a claim and the virtual view">
    <!-- road -->
    <rect x="10" y="74" width="580" height="140" fill="#dae1e6" />
    <line v-for="l in [1, 2]" :key="l" x1="10" x2="590" :y1="laneY(l) + laneH + 3" :y2="laneY(l) + laneH + 3"
          stroke="#fff" stroke-width="2" stroke-dasharray="14 10" />
    <template v-if="!bare">
      <text v-for="l in lanes" :key="`t${l}`" x="18" :y="laneY(l) + 26" class="lane">lane {{ l }} →</text>
    </template>

    <!-- virtual view of E: [pos(E) - h, pos(E) + h] over all lanes in view -->
    <rect x="96" y="70" width="400" height="148" fill="none" stroke="#002d4c" stroke-width="2" stroke-dasharray="7 5" />
    <g v-if="!bare">
    <text x="492" y="62" class="view" style="text-anchor:end">virtual view V(E)</text>
    <!-- arrowheads drawn as triangles, not markers: marker ids clash between mounted slides -->
    <line x1="296" x2="490" y1="234" y2="234" stroke="#445e6f" stroke-width="1.2" />
    <line x1="296" x2="102" y1="234" y2="234" stroke="#445e6f" stroke-width="1.2" />
    <path d="M496,234 L487,230 L487,238 Z" fill="#445e6f" />
    <path d="M96,234 L105,230 L105,238 Z" fill="#445e6f" />
    <line x1="296" x2="296" y1="226" y2="242" stroke="#445e6f" stroke-width="1.2" />
    <text x="400" y="250" class="h">h</text><text x="196" y="250" class="h">h</text>
    <text x="296" y="252" class="h">pos(E)</text>
    </g>

    <!-- C on lane 0: reservation + claim on lane 1 -->
    <rect x="150" :y="laneY(0) + 3" width="96" :height="laneH - 6" :fill="P.C.res" />
    <rect x="150" :y="laneY(1) + 3" width="96" :height="laneH - 6" fill="#fff" fill-opacity="0.35" :stroke="P.C.car" stroke-width="2" stroke-dasharray="5 4" />
    <text x="198" :y="laneY(1) + 25" class="atom">cl(C)</text>
    <CarGlyph :x="150" :y="laneY(0) + 8" :w="40" :h="24" label="C" :body="P.C.car" />

    <!-- E on lane 1 -->
    <rect x="278" :y="laneY(1) + 3" width="120" :height="laneH - 6" :fill="P.E.res" />
    <CarGlyph :x="278" :y="laneY(1) + 8" :w="40" :h="24" label="E" :body="P.E.car" />
    <text x="356" :y="laneY(1) + 25" class="atom">re(E)</text>

    <!-- B on lane 2 -->
    <rect x="300" :y="laneY(2) + 3" width="110" :height="laneH - 6" :fill="P.B.res" />
    <CarGlyph :x="300" :y="laneY(2) + 8" :w="40" :h="24" label="B" :body="P.B.car" />
    <text x="372" :y="laneY(2) + 25" class="atom">re(B)</text>

    <!-- A ahead, outside the view -->
    <rect x="520" :y="laneY(0) + 3" width="60" :height="laneH - 6" :fill="P.A.res" />
    <CarGlyph :x="520" :y="laneY(0) + 8" :w="40" :h="24" label="A" :body="P.A.car" />

    <!-- envelope brace for E -->
    <g v-if="!bare">
    <text x="215" y="20" class="note">reservation = safety envelope</text>
    <text x="215" y="36" class="note">car + stopping distance + buffer</text>
    <line x1="222" y1="42" x2="292" :y2="laneY(1) + 4" stroke="#445e6f" stroke-width="1" />
    </g>
  </svg>
</template>

<style scoped>
.mlsl { width: 100%; height: auto; font-family: var(--kit-font-body); }
.lane { font-size: 11px; fill: #445e6f; }
.view { font-size: 12px; font-weight: 700; fill: #002d4c; }
.h { font-size: 12px; font-style: italic; fill: #445e6f; text-anchor: middle; }
.atom { font-size: 13px; font-style: italic; fill: #002d4c; text-anchor: middle; }
.note { font-size: 11.5px; fill: #445e6f; text-anchor: middle; }
</style>
