<script setup lang="ts">
/*
 * KIT 2025 "title white vertical" (sdqbeamer.cls):
 *   green title box (width = right edge of grid column 3) | picture (2 columns + 3 gaps) |
 *   white logo box (1 column + margin) with the group logo at the bottom.
 *   KIT logo (rgb, 24 mm) at (297.5 mm, 1.03 cm).
 * The heading carries the full title and is centred vertically in the green box.
 */
defineProps<{
  heading: string
  subtitle?: string
  authors?: string
  event?: string
  date?: string
  image?: string
  imagePosition?: string
}>()
</script>

<template>
  <div class="slidev-layout kit-title">
    <div class="kit-title-green">
      <!-- the title is centred vertically in the space above the authors -->
      <div class="kit-title-main">
        <h1 class="kit-title-text">{{ heading }}</h1>
      </div>
      <div class="kit-title-sub">
        <div v-if="subtitle" class="sub">{{ subtitle }}</div>
        <div v-if="authors" class="authors">{{ authors }}</div>
        <div class="event">{{ event }}<template v-if="event && date"> | </template>{{ date }}</div>
      </div>
    </div>
    <div class="kit-title-picture">
      <img v-if="image" :src="image" :style="{ objectPosition: imagePosition ?? 'center' }" alt="">
    </div>
    <div class="kit-title-logobox">
      <img class="grouplogo" src="/logos/mase_logo.svg" alt="MASE group logo">
    </div>
    <img class="kitlogo" src="/logos/kitlogo_rgb.svg" alt="KIT">
    <slot />
  </div>
</template>

<style scoped>
.kit-title { position: relative; width: 100%; height: 100%; padding: 0; }
.kit-title-green {
  position: absolute; left: 0; top: 0; bottom: 0;
  width: 471.4px;                 /* \kitcolumnthreeright = 16.63 cm */
  background: var(--kit-green);
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  padding: var(--kit-margin) 0 var(--kit-bottom) var(--kit-margin);
}
.kit-title-main {
  flex: 1;
  display: flex;
  align-items: center;
  padding-bottom: 12px;
}
.kit-title-text {
  width: 425.2px;                 /* 3 columns + 2 gaps - 1 gap */
  color: var(--kit-green-20);
  font-size: 42px;
  line-height: 1.08;
  white-space: pre-line;          /* a newline in the heading starts a new line */
}
.kit-title-sub {
  width: 425.2px;
  color: #fff;
  font-size: 17px;
  line-height: 1.3;
}
.kit-title-sub .sub { font-weight: 700; margin-bottom: 0.35em; }
.kit-title-sub .authors { font-size: 14px; margin-bottom: 0.25em; }
.kit-title-sub .event { font-size: 14px; }
.kit-title-picture {
  position: absolute; top: 0; bottom: 0;
  left: 471.4px;
  width: 323.2px;                 /* 2 columns + 3 gaps = 11.4 cm */
  overflow: hidden;
  background: #fff;
}
.kit-title-picture img { width: 100%; height: 100%; object-fit: cover; display: block; }
.kit-title-logobox {
  position: absolute; top: 0; bottom: 0; right: 0;
  width: 165.3px;                 /* 1 column + margin */
  background: #fff;
}
.grouplogo {
  position: absolute;
  right: var(--kit-margin);
  bottom: var(--kit-bottom);
  width: 104.9px;                 /* max 37 mm x 20 mm */
  max-height: 56.7px;
  object-fit: contain;
}
.kitlogo {
  position: absolute;
  left: 843.3px;                  /* 297.5 mm */
  top: var(--kit-margin);
  width: 68px;                    /* 24 mm */
}
</style>
