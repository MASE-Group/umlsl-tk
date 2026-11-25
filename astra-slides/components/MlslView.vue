<script setup lang="ts">
/*
 * Highway model of MLSL: lanes (discrete), positions (continuous), reservations
 * (safety envelope), a claim (dashed) and the virtual view V(E) of the ego car E.
 * Neutral greys only: nothing here is safe or unsafe yet.
 */
const lanes = [0, 1, 2]
const laneY = (l: number) => 168 - l * 46   // lane 0 at the bottom
const laneH = 40
</script>

<template>
  <svg viewBox="0 0 600 260" class="mlsl" role="img" aria-label="Highway with reservations, a claim and the virtual view">
    <!-- road -->
    <rect x="10" y="74" width="580" height="140" fill="#dae1e6" />
    <line v-for="l in [1, 2]" :key="l" x1="10" x2="590" :y1="laneY(l) + laneH + 3" :y2="laneY(l) + laneH + 3"
          stroke="#fff" stroke-width="2" stroke-dasharray="14 10" />
    <text v-for="l in lanes" :key="`t${l}`" x="18" :y="laneY(l) + 26" class="lane">lane {{ l }} →</text>

    <!-- virtual view of E: [pos(E) - h, pos(E) + h] over all lanes in view -->
    <rect x="96" y="70" width="400" height="148" fill="none" stroke="#002d4c" stroke-width="2" stroke-dasharray="7 5" />
    <text x="492" y="62" class="view" style="text-anchor:end">virtual view V(E)</text>
    <line x1="296" x2="496" y1="234" y2="234" stroke="#445e6f" stroke-width="1.2" marker-end="url(#mh)" />
    <line x1="296" x2="96" y1="234" y2="234" stroke="#445e6f" stroke-width="1.2" marker-end="url(#mh)" />
    <line x1="296" x2="296" y1="226" y2="242" stroke="#445e6f" stroke-width="1.2" />
    <text x="400" y="250" class="h">h</text><text x="196" y="250" class="h">h</text>
    <text x="296" y="252" class="h">pos(E)</text>
    <defs>
      <marker id="mh" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
        <path d="M0,0L10,5L0,10Z" fill="#445e6f" />
      </marker>
    </defs>

    <!-- C on lane 0: reservation + claim on lane 1 -->
    <rect x="150" :y="laneY(0) + 3" width="96" :height="laneH - 6" fill="#a8b9c4" />
    <rect x="150" :y="laneY(1) + 3" width="96" :height="laneH - 6" fill="none" stroke="#445e6f" stroke-width="2" stroke-dasharray="5 4" />
    <text x="198" :y="laneY(1) + 25" class="atom">cl(C)</text>
    <rect x="150" :y="laneY(0) + 9" width="34" height="22" rx="3" fill="#002d4c" />
    <text x="167" :y="laneY(0) + 25" class="car">C</text>

    <!-- E on lane 1 -->
    <rect x="278" :y="laneY(1) + 3" width="120" :height="laneH - 6" fill="#a8b9c4" />
    <rect x="278" :y="laneY(1) + 9" width="34" height="22" rx="3" fill="#002d4c" />
    <text x="295" :y="laneY(1) + 25" class="car">E</text>
    <text x="356" :y="laneY(1) + 25" class="atom">re(E)</text>

    <!-- B on lane 2 -->
    <rect x="300" :y="laneY(2) + 3" width="110" :height="laneH - 6" fill="#a8b9c4" />
    <rect x="300" :y="laneY(2) + 9" width="34" height="22" rx="3" fill="#002d4c" />
    <text x="317" :y="laneY(2) + 25" class="car">B</text>
    <text x="372" :y="laneY(2) + 25" class="atom">re(B)</text>

    <!-- A ahead, outside the view -->
    <rect x="520" :y="laneY(0) + 3" width="60" :height="laneH - 6" fill="#a8b9c4" />
    <rect x="520" :y="laneY(0) + 9" width="34" height="22" rx="3" fill="#002d4c" />
    <text x="537" :y="laneY(0) + 25" class="car">A</text>

    <!-- envelope brace for E -->
    <text x="215" y="20" class="note">reservation = safety envelope</text>
    <text x="215" y="36" class="note">car + stopping distance + buffer</text>
    <line x1="222" y1="42" x2="292" :y2="laneY(1) + 4" stroke="#445e6f" stroke-width="1" />
  </svg>
</template>

<style scoped>
.mlsl { width: 100%; height: auto; font-family: var(--kit-font-body); }
.lane { font-size: 15px; fill: #445e6f; }
.view { font-size: 15px; font-weight: 700; fill: #002d4c; }
.h { font-size: 15px; font-style: italic; fill: #445e6f; text-anchor: middle; }
.car { font-size: 15px; font-weight: 700; fill: #fff; text-anchor: middle; }
.atom { font-size: 15px; font-style: italic; fill: #002d4c; text-anchor: middle; }
.note { font-size: 15px; fill: #445e6f; text-anchor: middle; }
</style>
