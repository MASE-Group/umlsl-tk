<script setup lang="ts">
/*
 * KIT 2025 "picture 33/50/66 vertical" (sdqbeamer.cls): text on the left, a full-height
 * picture on the right from grid column 5/4/3, narrow footline without navigation.
 */
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  image: string
  split?: 33 | 50 | 66
  fit?: 'cover' | 'contain'
  bg?: string
  imagePosition?: string
  kitlogo?: 'rgb' | 'white'
}>(), { split: 50, fit: 'cover', bg: '#fff', imagePosition: 'center', kitlogo: 'white' })

// left edge of the picture: \kitcolumnfiveleft / fourleft / threeleft
const left = computed(() => ({ 33: 641.5, 50: 488.4, 66: 335.4 } as const)[props.split])
const colsep = 17
const footerTitle = computed(() => left.value - 29.2 - 136)
</script>

<template>
  <div class="slidev-layout kit-picture">
    <div class="kit-pic" :style="{ left: `${left}px`, background: bg }">
      <img :src="image" :style="{ objectFit: fit, objectPosition: imagePosition }" alt="">
    </div>
    <div class="kit-body" :style="{ right: `${960 - left + colsep}px` }">
      <slot />
    </div>
    <KitFooter variant="picture" :title-width="footerTitle" :kitlogo="kitlogo" />
  </div>
</template>

<style scoped>
.kit-picture { position: relative; width: 100%; height: 100%; padding: 0; }
.kit-pic { position: absolute; top: 0; right: 0; bottom: 0; overflow: hidden; }
.kit-pic img { width: 100%; height: 100%; display: block; }
.kit-body {
  position: absolute;
  top: var(--kit-content-top);
  left: var(--kit-margin);
  bottom: calc(var(--kit-bottom) + 6px);
}
.kit-body :deep(h1) {
  position: absolute;
  top: calc(var(--kit-margin) - var(--kit-content-top));
  left: 0;
  right: 0;
  font-size: 36px;
  line-height: 1.1;
}
</style>
