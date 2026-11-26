<script setup lang="ts">
/*
 * KIT 2025 footline (sdqbeamer.cls): section navigation dots, page number "n/total",
 * short date, "author: short title", group name and the KIT logo.
 * variant "picture" = footline of picture frames: no navigation, no group name.
 * Backup slides (from `section: Backup` on) show "B1", "B2", ... instead of "n/total".
 */
import { computed } from 'vue'
import { useNav, useSlideContext } from '@slidev/client'

const props = withDefaults(defineProps<{
  variant?: 'full' | 'picture'
  titleWidth?: number
  kitlogo?: 'rgb' | 'white'
}>(), { variant: 'full', titleWidth: 459, kitlogo: 'rgb' })

const { slides, total } = useNav()
const { $page, $slidev } = useSlideContext()
const cfg = computed(() => ($slidev.configs as any).kit ?? {})

// Backup slides start at the first slide with `section: Backup`. They are numbered B1, B2, ...
// and kept out of the page total and the section navigation of the talk.
const BACKUP = 'Backup'
const firstBackup = computed(() => {
  const s = slides.value.find(s => (s.meta?.slide?.frontmatter as any)?.section === BACKUP)
  return s ? s.no : null
})
const mainTotal = computed(() => (firstBackup.value ? firstBackup.value - 1 : total.value))
const pageLabel = computed(() => (firstBackup.value && $page.value >= firstBackup.value
  ? `B${$page.value - firstBackup.value + 1}`
  : `${$page.value}/${mainTotal.value}`))

const sections = computed(() => {
  const out: { name: string, pages: number[] }[] = []
  let cur: { name: string, pages: number[] } | null = null
  for (const s of slides.value) {
    const fm: any = s.meta?.slide?.frontmatter ?? {}
    if (fm.layout === 'title')
      continue
    if (fm.section === BACKUP)
      break
    if (fm.section) {
      cur = { name: fm.section, pages: [] }
      out.push(cur)
    }
    if (cur)
      cur.pages.push(s.no)
  }
  return out
})
</script>

<template>
  <div class="kit-footer-wrap" :class="variant">
    <nav v-if="variant === 'full'" class="kit-nav">
      <div
        v-for="sec in sections" :key="sec.name"
        class="kit-nav-sec" :class="{ current: sec.pages.includes($page) }"
      >
        <span class="kit-nav-name">{{ sec.name }}</span>
        <span class="kit-nav-dots">
          <i v-for="p in sec.pages" :key="p" :class="{ on: p === $page }" />
        </span>
      </div>
    </nav>
    <div class="kit-foot">
      <div class="kit-foot-page">{{ pageLabel }}</div>
      <div class="kit-foot-date">{{ cfg.shortdate }}</div>
      <div class="kit-foot-title" :style="{ width: `${variant === 'full' ? 459 : titleWidth}px` }">
        {{ cfg.shortauthor }}: {{ cfg.shorttitle }}
      </div>
      <div v-if="variant === 'full'" class="kit-foot-group">{{ cfg.groupname }}</div>
      <div v-else class="kit-foot-spacer" />
      <div class="kit-foot-logo">
        <img :src="kitlogo === 'white' ? '/logos/kitlogo_white.svg' : '/logos/kitlogo_rgb.svg'" alt="KIT">
      </div>
    </div>
  </div>
</template>

<style scoped>
.kit-footer-wrap {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  font-family: var(--kit-font-body);
  font-size: 12px;
  color: var(--kit-footer);
  z-index: 10;
}
.kit-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: var(--kit-nav-h);
  padding: 0 21.3px;   /* 7.5 mm */
  font-size: 10.5px;
}
.kit-nav-sec { display: flex; align-items: center; gap: 5px; opacity: 0.55; }
.kit-nav-sec.current { opacity: 1; }
.kit-nav-dots { display: inline-flex; gap: 2.5px; }
.kit-nav-dots i {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  border: 1px solid var(--kit-footer);
  box-sizing: border-box;
}
.kit-nav-dots i.on { background: var(--kit-footer); }

.kit-foot {
  display: flex;
  align-items: center;
  height: var(--kit-bottom);
}
.kit-foot-page {
  width: 74.6px;           /* margin + 16 mm */
  padding-left: var(--kit-margin);
  font-weight: 700;
  box-sizing: border-box;
}
.kit-foot-date { width: 87.9px; }   /* 31 mm */
.kit-foot-title { line-height: 1.15; }
.kit-foot-group { width: 252.3px; line-height: 1.15; }   /* 89 mm */
.kit-foot-spacer { flex: 1; }
.kit-foot-logo { width: 51px; }     /* 18 mm */
.kit-foot-logo img { width: 100%; display: block; position: relative; top: -2px; }
</style>
