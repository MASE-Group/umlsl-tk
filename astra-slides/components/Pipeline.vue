<script setup lang="ts">
// Fig. 1 of the paper: high-level architecture of UMLSL-TK (brand green frames the toolkit).
</script>

<template>
  <svg viewBox="0 0 600 230" class="pipe" role="img" aria-label="UMLSL-TK architecture">
    <defs>
      <marker id="pa" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
        <path d="M0,0L10,5L0,10Z" fill="#445e6f" />
      </marker>
    </defs>
    <rect x="4" y="4" width="592" height="222" fill="none" stroke="#009682" stroke-width="2" />
    <text x="300" y="218" class="tk">UMLSL-TK</text>

    <text x="120" y="30" class="tool">UMLSL-Edit</text>
    <text x="480" y="30" class="tool">UMLSL-Sim</text>
    <rect x="30" y="42" width="180" height="150" class="tbox" />
    <rect x="390" y="42" width="180" height="150" class="tbox" />

    <rect x="50" y="56" width="140" height="44" class="comp" /><text x="120" y="83" class="ct">Scenario editor</text>
    <rect x="50" y="136" width="140" height="44" class="comp" /><text x="120" y="163" class="ct">Model checker</text>
    <line x1="120" x2="120" y1="100" y2="134" stroke="#445e6f" stroke-width="2" marker-end="url(#pa)" />
    <text x="128" y="122" class="lbl" style="text-anchor:start">verify</text>

    <rect x="410" y="56" width="140" height="44" class="comp" /><text x="480" y="76" class="ct">Discrete-time</text><text x="480" y="92" class="ct">simulation</text>
    <rect x="410" y="136" width="140" height="44" class="comp" /><text x="480" y="163" class="ct">RL training</text>
    <line x1="480" x2="480" y1="100" y2="134" stroke="#445e6f" stroke-width="2" marker-end="url(#pa)" />
    <text x="488" y="122" class="lbl" style="text-anchor:start">observe &amp; analyse</text>

    <line x1="192" x2="406" y1="78" y2="78" stroke="#445e6f" stroke-width="2" marker-end="url(#pa)" />
    <text x="300" y="70" class="lbl">verified scenario</text>
    <line x1="408" x2="194" y1="158" y2="158" stroke="#445e6f" stroke-width="2" marker-end="url(#pa)" />
    <text x="300" y="150" class="lbl">simulation snapshot</text>
  </svg>
</template>

<style scoped>
.pipe { width: 100%; height: auto; font-family: var(--kit-font-body); }
.tbox { fill: #edf1f3; stroke: #a8b9c4; stroke-width: 1.2; }
.comp { fill: #fff; stroke: #002d4c; stroke-width: 1.5; }
.tool { font-size: 15px; font-weight: 700; fill: #002d4c; text-anchor: middle; font-family: var(--kit-font-title); }
.ct { font-size: 13px; fill: #002d4c; text-anchor: middle; }
.lbl { font-size: 12px; font-style: italic; fill: #445e6f; text-anchor: middle; }
.tk { font-size: 13px; font-weight: 700; fill: #009682; text-anchor: middle; }
</style>
