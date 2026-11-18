<script setup lang="ts">
/*
 * Tiny picture of what one rule of the recursive check does to the observed space.
 *   atom  : one lane, one interval test
 *   same  : the same space
 *   cars  : the same space, once per car in the view
 *   vchop : split at a lane border
 *   hchop : split at a point r (r continuous: marked "?")
 */
defineProps<{ kind: 'atom' | 'same' | 'cars' | 'vchop' | 'hchop' }>()
</script>

<template>
  <svg viewBox="0 0 96 40" class="glyph" aria-hidden="true">
    <template v-if="kind === 'atom'">
      <rect x="6" y="13" width="84" height="14" class="sp" />
      <rect x="22" y="13" width="44" height="14" class="res" />
    </template>
    <template v-else-if="kind === 'same'">
      <rect x="6" y="4" width="84" height="32" class="sp" />
    </template>
    <template v-else-if="kind === 'cars'">
      <rect x="14" y="2" width="74" height="26" class="sp" />
      <rect x="10" y="6" width="74" height="26" class="sp" />
      <rect x="6" y="10" width="74" height="26" class="sp" />
    </template>
    <template v-else-if="kind === 'vchop'">
      <rect x="6" y="4" width="84" height="14" class="sp" />
      <rect x="6" y="22" width="84" height="14" class="sp" />
    </template>
    <template v-else>
      <rect x="6" y="4" width="46" height="32" class="sp" />
      <rect x="56" y="4" width="34" height="32" class="sp" />
      <text x="54" y="25" class="q">?</text>
    </template>
  </svg>
</template>

<style scoped>
.glyph { width: 72px; height: 30px; flex: none; }
.sp { fill: #edf1f3; stroke: #445e6f; stroke-width: 1.5; }
.res { fill: #a8b9c4; }
.q { font-size: 15px; font-weight: 700; fill: #002d4c; text-anchor: middle; font-family: var(--kit-font-body); }
</style>
