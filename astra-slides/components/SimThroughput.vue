<script setup lang="ts">
// Paper Table 3; repository UMLSL-Sim/benchmarks/results/two_crossings/throughput.json.
const rows = [{cars:16,fps:257},{cars:24,fps:128},{cars:32,fps:55.9},{cars:40,fps:47.6},{cars:48,fps:28.5}]
</script>
<template>
<svg viewBox="0 0 560 300" role="img" aria-label="Simulation frames per second: 257 with 16 cars, 128 with 24, 55.9 with 32, 47.6 with 40, 28.5 with 48">
<g font-family="Helvetica Neue, Arial, sans-serif" fill="#002d4c">
<text x="0" y="22" style="font-size:19px">cars</text><text x="87" y="22" style="font-size:20px" font-weight="700">simulation frames / second</text>
<g v-for="(r,i) in rows" :key="r.cars">
<text x="18" :y="63+i*48" style="font-size:22px">{{ r.cars }}</text>
<rect x="87" :y="39+i*48" :width="r.fps/257*365" height="32" fill="#445e6f"/>
<text :x="99+r.fps/257*365" :y="63+i*48" style="font-size:22px" font-weight="700">{{ r.fps }}</text>
</g>
<text x="87" y="294" style="font-size:16px" fill="#445e6f">Mean of per-seed best frame times; 3 seeds × 5 repeats</text>
</g></svg>
</template>
