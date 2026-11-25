<script setup lang="ts">
// The two chopping operators on an observed space V = (L, [b, e]).
</script>

<template>
  <svg viewBox="0 0 600 210" class="chop" role="img" aria-label="Horizontal and vertical chop">
    <!-- horizontal chop -->
    <text x="140" y="18" class="ttl">horizontal chop  φ₁ ⌢ φ₂</text>
    <rect x="20" y="34" width="150" height="120" class="pa" />
    <rect x="170" y="34" width="100" height="120" class="pb" />
    <line x1="20" x2="270" y1="94" y2="94" class="lane" />
    <line x1="170" x2="170" y1="28" y2="160" class="cut" />
    <text x="95" y="99" class="phi">φ₁</text>
    <text x="220" y="99" class="phi">φ₂</text>
    <g class="tick">
      <line x1="20" x2="20" y1="154" y2="164" /><line x1="170" x2="170" y1="154" y2="164" /><line x1="270" x2="270" y1="154" y2="164" />
    </g>
    <text x="20" y="180" class="pt">b</text>
    <text x="170" y="180" class="pt">r</text>
    <text x="270" y="180" class="pt">e</text>
    <text x="145" y="202" class="sub">split at a point r along the lanes</text>

    <!-- vertical chop -->
    <text x="460" y="18" class="ttl">vertical chop</text>
    <g class="frac">
      <text x="548" y="13" class="fr">φ₂</text>
      <line x1="538" x2="560" y1="17" y2="17" stroke="#002d4c" stroke-width="1.2" />
      <text x="548" y="30" class="fr">φ₁</text>
    </g>
    <rect x="350" y="34" width="220" height="40" class="pb" />
    <rect x="350" y="74" width="220" height="80" class="pa" />
    <line x1="350" x2="570" y1="114" y2="114" class="lane" />
    <line x1="344" x2="576" y1="74" y2="74" class="cut" />
    <text x="460" y="59" class="phi">φ₂</text>
    <text x="460" y="119" class="phi">φ₁</text>
    <text x="340" y="58" class="pt" style="text-anchor:end">k+1…j</text>
    <text x="340" y="118" class="pt" style="text-anchor:end">i…k</text>
    <text x="460" y="202" class="sub">split at a lane border</text>
  </svg>
</template>

<style scoped>
.chop { width: 100%; height: auto; font-family: var(--kit-font-body); }
.pa { fill: #edf1f3; stroke: #a8b9c4; stroke-width: 1.5; }
.pb { fill: #dae1e6; stroke: #a8b9c4; stroke-width: 1.5; }
.lane { stroke: #fff; stroke-width: 2; stroke-dasharray: 10 7; }
.cut { stroke: #002d4c; stroke-width: 2.5; }
.phi { font-size: 20px; font-style: italic; fill: #002d4c; text-anchor: middle; }
.ttl { font-size: 15px; font-weight: 700; fill: #002d4c; text-anchor: middle; }
.fr { font-size: 13px; font-style: italic; fill: #002d4c; text-anchor: middle; }
.pt { font-size: 15px; font-style: italic; fill: #445e6f; text-anchor: middle; }
.sub { font-size: 15px; fill: #445e6f; text-anchor: middle; }
.tick line { stroke: #445e6f; stroke-width: 1.5; }
</style>
