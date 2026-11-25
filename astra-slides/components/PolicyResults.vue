<script setup lang="ts">
// Paper Table 4. Goals: mean total over 30 evaluation episodes per seed, 3 seeds.
const rows = [
{label:'Random',crash:74,goals:28.3},
{label:'Random + shield',crash:0,goals:31.0},
{label:'PPO · initial reward',crash:43,goals:20.3},
{label:'PPO · safety-aware reward',crash:0,goals:0.0},
{label:'MaskablePPO + shield',crash:0,goals:41.0},
]
</script>
<template>
<svg viewBox="0 0 900 275" role="img" aria-label="Policy comparison: random 74% crash and 28.3 goals; shielded random 0% and 31 goals; PPO initial 43% and 20.3 goals; safety-aware PPO 0% and 0 goals; shielded MaskablePPO 0% and 41 goals">
<g font-family="Helvetica Neue, Arial, sans-serif" fill="#002d4c">
<text x="8" y="24" style="font-size:19px" font-weight="700">Policy</text><text x="345" y="24" style="font-size:19px" font-weight="700">Crash rate</text><text x="600" y="24" style="font-size:19px" font-weight="700">Goals / 30 episodes</text>
<g v-for="(r,i) in rows" :key="r.label">
<rect x="0" :y="36+i*46" width="900" height="43" :fill="i===4?'#d9efec':i%2===0?'#edf1f3':'#fff'"/>
<text x="8" :y="64+i*46" style="font-size:19px" :font-weight="i===4?700:400">{{ r.label }}</text>
<rect x="345" :y="46+i*46" :width="r.crash/100*200" height="22" fill="#a22223"/>
<text :x="355+r.crash/100*200" :y="64+i*46" style="font-size:20px" :fill="r.crash?'#a22223':'#009682'">{{r.crash}}%</text>
<rect x="600" :y="46+i*46" :width="r.goals/41*220" height="22" fill="#445e6f"/>
<text :x="610+r.goals/41*220" :y="64+i*46" style="font-size:20px" font-weight="700">{{r.goals.toFixed(1)}}</text>
</g></g></svg>
</template>
