<script setup lang="ts">
/*
 * Fig. 4 of the paper: the claim-check-reserve flow as a timed automaton over clock x,
 * shared by the lane-change controller [20] and the crossing controller [32].
 * Colour: red = potential collision (withdraw), green = safe (reserve), grey/ink = rest.
 */
import { computed, useId } from 'vue'

// Marker ids must be unique per instance: slides 5 and 7 both use this diagram, and a
// url(#id) that resolves into the other (hidden) slide draws no arrowhead.
const uid = useId()
const m = (c: string) => `url(#ah-${c}-${uid})`

const props = withDefaults(defineProps<{ variant?: 'lane' | 'crossing' }>(), { variant: 'lane' })

const a = computed(() => props.variant === 'lane'
  ? { claim: 'c(ego, n)', wdClaim: 'wd c(ego)', reserve: 'r(ego)', wdRes: 'wd r(ego, n)' }
  : { claim: 'cc(ego)', wdClaim: 'wd cc(ego)', reserve: 'rc(ego)', wdRes: 'wd rc(ego)' })
</script>

<template>
  <svg viewBox="0 0 560 272" class="ta" role="img" aria-label="Claim, check, reserve timed automaton">
    <defs>
      <marker :id="`ah-ink-${uid}`" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4.5" markerHeight="4.5" orient="auto-start-reverse">
        <path d="M0,0L10,5L0,10Z" fill="#445e6f" />
      </marker>
      <marker :id="`ah-red-${uid}`" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4.5" markerHeight="4.5" orient="auto-start-reverse">
        <path d="M0,0L10,5L0,10Z" fill="#a22223" />
      </marker>
      <marker :id="`ah-green-${uid}`" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4.5" markerHeight="4.5" orient="auto-start-reverse">
        <path d="M0,0L10,5L0,10Z" fill="#009682" />
      </marker>
    </defs>

    <!-- initial arrow -->
    <line x1="20" y1="78" x2="58" y2="78" stroke="#445e6f" stroke-width="2" :marker-end="m('ink')" />

    <!-- states -->
    <g class="state">
      <rect x="60" y="56" width="110" height="44" rx="22" />
      <text x="115" y="84">idle</text>
    </g>
    <g class="state">
      <rect x="390" y="56" width="130" height="44" rx="22" />
      <text x="455" y="84">claiming</text>
    </g>
    <g class="state">
      <rect x="215" y="196" width="130" height="44" rx="22" />
      <text x="280" y="224">reserving</text>
    </g>

    <!-- invariants -->
    <text x="418" y="124" class="inv">¬pc(ego) ∧ x ≤ t<tspan class="sb" dy="3">cl</tspan></text>
    <text x="280" y="260" class="inv">x ≤ t<tspan class="sb" dy="3">re</tspan></text>

    <!-- idle -> claiming -->
    <path d="M150,58 C230,20 330,20 410,58" fill="none" stroke="#445e6f" stroke-width="2" :marker-end="m('ink')" />
    <text x="280" y="16" class="lbl">claim {{ a.claim }}; x := 0</text>

    <!-- claiming -> idle : potential collision -->
    <path d="M390,86 L172,86" fill="none" stroke="#a22223" stroke-width="2" :marker-end="m('red')" />
    <text x="281" y="78" class="lbl red">pc(ego) / withdraw {{ a.wdClaim }}</text>

    <!-- claiming -> reserving : no potential collision -->
    <path d="M500,100 C500,170 420,215 347,218" fill="none" stroke="#009682" stroke-width="2" :marker-end="m('green')" />
    <text x="448" y="160" class="lbl green" style="text-anchor:end">¬pc(ego) / reserve {{ a.reserve }}</text>
    <text x="448" y="176" class="lbl green" style="text-anchor:end">x := 0</text>

    <!-- reserving -> idle -->
    <path d="M215,214 C160,200 120,160 112,102" fill="none" stroke="#445e6f" stroke-width="2" :marker-end="m('ink')" />
    <text x="104" y="166" class="lbl" style="text-anchor:end">x ≥ t<tspan class="sb" dy="3">re</tspan><tspan dy="-3"> /</tspan></text>
    <text x="104" y="182" class="lbl" style="text-anchor:end">{{ a.wdRes }}</text>
  </svg>
</template>

<style scoped>
.ta { width: 100%; height: auto; font-family: var(--kit-font-body); }
.state rect { fill: #edf1f3; stroke: #002d4c; stroke-width: 2; }
.state text { font-size: 15px; font-weight: 700; fill: #002d4c; text-anchor: middle; }
.lbl { font-size: 12.5px; fill: #002d4c; text-anchor: middle; font-style: italic; }
.lbl.red { fill: #a22223; }
.lbl.green { fill: #009682; }
.sb { font-size: 9px !important; }
.inv { font-size: 12px; fill: #445e6f; text-anchor: middle; font-style: italic; }
</style>
