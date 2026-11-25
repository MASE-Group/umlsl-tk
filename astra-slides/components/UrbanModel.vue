<script setup lang="ts">
import { useId } from 'vue'
const markerId = `urban-arrow-${useId()}`
/*
 * Urban traffic model: lane segments (numbers) and crossing segments c0..c3,
 * a crossing reservation of D (whole path + its own length beyond the crossing),
 * and the virtual view of E whose virtual lanes run through the crossing.
 */
</script>

<template>
  <svg viewBox="0 0 600 300" class="urban" role="img" aria-label="Intersection with lane and crossing segments">
    <defs>
      <marker :id="markerId" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
        <path d="M0,0L10,5L0,10Z" fill="#445e6f" />
      </marker>
    </defs>
    <!-- roads -->
    <rect x="10" y="120" width="580" height="80" fill="#dae1e6" />
    <rect x="300" y="10" width="80" height="280" fill="#dae1e6" />
    <line x1="10" x2="300" y1="160" y2="160" class="mid" /><line x1="380" x2="590" y1="160" y2="160" class="mid" />
    <line x1="340" x2="340" y1="10" y2="120" class="mid" /><line x1="340" x2="340" y1="200" y2="290" class="mid" />

    <!-- crossing segments -->
    <g class="cs">
      <rect x="300" y="120" width="40" height="40" /><rect x="340" y="120" width="40" height="40" />
      <rect x="300" y="160" width="40" height="40" /><rect x="340" y="160" width="40" height="40" />
    </g>


    <!-- lane segment ids and driving directions (directed edges) -->
    <text x="30" y="185" class="seg">0</text><text x="565" y="185" class="seg">1</text>
    <text x="565" y="145" class="seg">2</text><text x="30" y="145" class="seg">3</text>
    <line x1="230" x2="262" y1="180" y2="180" :marker-end="`url(#${markerId})`" class="dir" />
    <line x1="470" x2="502" y1="180" y2="180" :marker-end="`url(#${markerId})`" class="dir" />
    <line x1="502" x2="470" y1="140" y2="140" :marker-end="`url(#${markerId})`" class="dir" />
    <line x1="262" x2="230" y1="140" y2="140" :marker-end="`url(#${markerId})`" class="dir" />
    <line x1="320" x2="320" y1="230" y2="262" :marker-end="`url(#${markerId})`" class="dir" />
    <line x1="360" x2="360" y1="262" y2="230" :marker-end="`url(#${markerId})`" class="dir" />
    <line x1="360" x2="360" y1="70" y2="38" :marker-end="`url(#${markerId})`" class="dir" />

    <!-- D: reservation through the crossing (turns right), plus its own length beyond -->
    <path d="M302,40 L338,40 L338,158 L262,158 L262,122 L302,122 Z" class="res" />
    <rect x="304" y="40" width="32" height="20" rx="3" class="car" />
    <text x="320" y="55" class="carl">D</text>
    <text x="246" y="112" class="atom">re(D)</text>

    <!-- E: reservation ends before the crossing -->
    <rect x="120" y="163" width="110" height="34" class="res" />
    <rect x="120" y="170" width="34" height="20" rx="3" class="car" />
    <text x="137" y="185" class="carl">E</text>
    <text x="196" y="185" class="atom">re(E)</text>
    <!-- gap brace -->
    <line x1="230" x2="300" y1="214" y2="214" stroke="#445e6f" stroke-width="1.2" />
    <line x1="230" x2="230" y1="208" y2="220" stroke="#445e6f" stroke-width="1.2" />
    <line x1="300" x2="300" y1="208" y2="220" stroke="#445e6f" stroke-width="1.2" />
    <text x="265" y="232" class="note">gap</text>

    <!-- E's virtual view through the crossing -->
    <rect x="60" y="116" width="420" height="88" fill="none" stroke="#002d4c" stroke-width="2" stroke-dasharray="7 5" />
    <text x="64" y="110" class="view">V(E)</text>

    <text x="320" y="144" class="seg">c0</text><text x="360" y="144" class="seg">c1</text>
    <text x="320" y="184" class="seg">c2</text><text x="360" y="184" class="seg">c3</text>
    <!-- legend by labels -->
    <text x="20" y="250" class="note" style="text-anchor:start">lane segments: 0, 1, 2, …</text>
    <text x="20" y="268" class="note" style="text-anchor:start">crossing segments: c0 … c3</text>
  </svg>
</template>

<style scoped>
.urban { width: 100%; height: auto; font-family: var(--kit-font-body); }
.mid { stroke: #fff; stroke-width: 2; stroke-dasharray: 12 8; }
.cs rect { fill: #c7d3db; stroke: #fff; stroke-width: 1; stroke-dasharray: 3 3; }
.seg { font-size: 15px; fill: #445e6f; text-anchor: middle; }
.dir { stroke: #445e6f; stroke-width: 1.5; }
.res { fill: #a8b9c4; opacity: 0.9; }
.car { fill: #002d4c; }
.carl { font-size: 15px; font-weight: 700; fill: #fff; text-anchor: middle; }
.atom { font-size: 15px; font-style: italic; fill: #002d4c; text-anchor: middle; }
.note { font-size: 15px; fill: #445e6f; text-anchor: middle; }
.view { font-size: 15px; font-weight: 700; fill: #002d4c; }
</style>
