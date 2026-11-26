<script setup lang="ts">
// KIT 2025 standard frame: title top-left at the outer margin, content from 37 mm, footline.
defineProps<{ subtitle?: string }>()
</script>

<template>
  <div class="slidev-layout kit-default">
    <div class="kit-body">
      <slot />
    </div>
    <div v-if="subtitle" class="kit-subtitle">{{ subtitle }}</div>
    <KitFooter variant="full" />
  </div>
</template>

<style scoped>
.kit-default {
  position: relative;
  width: 100%;
  height: 100%;
  padding: 0;
}
.kit-body {
  position: absolute;
  top: var(--kit-content-top);
  left: var(--kit-margin);
  right: var(--kit-margin);
  bottom: calc(var(--kit-bottom) + var(--kit-nav-h) + 4px);
}
.kit-body :deep(h1) {
  position: absolute;
  top: calc(var(--kit-margin) - var(--kit-content-top));
  left: 0;
  right: 70px;
  font-size: 36px;            /* \huge */
  line-height: 1.1;
}
.kit-subtitle {
  position: absolute;
  top: calc(var(--kit-margin) + 42px);
  left: var(--kit-margin);
  font-family: var(--kit-font-title);
  font-weight: 600;
  font-size: 22px;
  color: var(--kit-iceblue-50);
}
</style>
