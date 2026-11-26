<script setup lang="ts">
// Inline KaTeX for places where markdown math is not parsed (inside raw HTML blocks).
import katex from 'katex'
import { computed } from 'vue'

const props = defineProps<{ e: string, display?: boolean }>()
const html = computed(() => katex.renderToString(props.e, { throwOnError: false, displayMode: !!props.display }))
</script>

<template>
  <span class="tex" v-html="html" />
</template>
