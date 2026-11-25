// Overflow check: opens every slide (all clicks revealed) and reports elements that leave
// the content box of the KIT layout or the slide canvas, or that overlap the footer.
// Usage: start `npx slidev --port 3030` in another shell, then `npm run check`.
import { chromium } from 'playwright-chromium'
import { mkdir, writeFile } from 'node:fs/promises'
await mkdir('preview', { recursive: true })

const BASE = process.env.BASE ?? 'http://localhost:3030'
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } })

await page.goto(`${BASE}/1`, { waitUntil: 'networkidle' })
const total = await page.evaluate(() => window.__slidev__?.nav?.total ?? null)
const count = total ?? Number(process.env.SLIDES ?? 0)
if (!count)
  throw new Error('Could not read the slide count. Set SLIDES=<n>.')

let problems = 0
for (let n = 1; n <= count; n++) {
  await page.goto(`${BASE}/${n}?clicks=99`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(400)
  await page.evaluate(() => document.fonts.ready)
  await page.screenshot({ path: `preview/slide-${String(n).padStart(2, '0')}.png` })
  const res = await page.evaluate(() => {
    const out = []
    // the dev server keeps neighbouring slides mounted but hidden: take the visible one
    const layout = [...document.querySelectorAll('.slidev-layout')].find((el) => {
      const r = el.getBoundingClientRect()
      return r.width > 0 && r.height > 0 && el.offsetParent !== null && getComputedStyle(el).visibility !== 'hidden'
    })
    if (!layout)
      return ['no layout found']
    const L = layout.getBoundingClientRect()
    const scale = L.width / 960
    const tol = 1.5 * scale
    const describe = (el) => {
      const t = (el.textContent ?? '').trim().replace(/\s+/g, ' ').slice(0, 50)
      return `<${el.tagName.toLowerCase()} class="${el.getAttribute('class') ?? ''}"> "${t}"`
    }
    const visible = (el) => {
      const cs = getComputedStyle(el)
      if (cs.display === 'none' || cs.visibility === 'hidden' || Number(cs.opacity) === 0)
        return false
      const r = el.getBoundingClientRect()
      return r.width > 0 && r.height > 0
    }
    // 1. nothing may leave the slide canvas
    for (const el of layout.querySelectorAll('*')) {
      if (!visible(el) || el.matches('.crop-frame img') || el.closest('.katex') || el.closest('svg') && el.tagName !== 'svg')
        continue
      const r = el.getBoundingClientRect()
      if (r.right > L.right + tol || r.bottom > L.bottom + tol || r.left < L.left - tol || r.top < L.top - tol)
        out.push(`outside canvas: ${describe(el)}`)
    }
    // 2. content must stay inside the content box (above navigation + footer)
    const body = layout.querySelector('.kit-body')
    if (body) {
      const B = body.getBoundingClientRect()
      var slack = Infinity
      const footer = layout.querySelector('.kit-footer-wrap')
      const F = footer ? footer.getBoundingClientRect() : null
      for (const el of body.querySelectorAll('*')) {
        if (!visible(el) || el.matches('.crop-frame img') || el.closest('.katex') || el.closest('svg') && el.tagName !== 'svg')
          continue
        slack = Math.min(slack, (B.bottom - el.getBoundingClientRect().bottom) / scale)
        if (el.tagName === 'H1')
          continue // the title sits in the header band by design
        const r = el.getBoundingClientRect()
        if (r.bottom > B.bottom + tol)
          out.push(`below content box by ${((r.bottom - B.bottom) / scale).toFixed(1)}px: ${describe(el)}`)
        if (r.right > B.right + tol)
          out.push(`right of content box by ${((r.right - B.right) / scale).toFixed(1)}px: ${describe(el)}`)
        if (F && r.bottom > F.top + tol)
          out.push(`overlaps footer: ${describe(el)}`)
      }
      const source = body.querySelector('.source')
      if (source) {
        const S=source.getBoundingClientRect()
        for (const el of body.children) {
          if(el===source || el.tagName==='H1' || !visible(el)) continue
          const r=el.getBoundingClientRect()
          if(r.bottom > S.top - 3*scale) out.push(`content meets source line: ${describe(el)}`)
        }
      }
      // SVG text can overflow even when its parent fits the content box.
      for (const svg of body.querySelectorAll('svg')) {
        const S=svg.getBoundingClientRect()
        for (const t of svg.querySelectorAll('text')) {
          if(!visible(t)) continue
          const T=t.getBoundingClientRect()
          if(T.left<S.left-tol || T.right>S.right+tol || T.top<S.top-tol || T.bottom>S.bottom+tol)
            out.push(`SVG label outside figure: ${describe(t)}`)
        }
      }
      const h1 = body.querySelector('h1')
      if (h1 && h1.getBoundingClientRect().bottom > B.top + tol)
        out.push(`title runs into the content area: ${describe(h1)}`)
    }
    return { out: [...new Set(out)], slack: typeof slack === 'number' ? slack : null }
  })
  const list = Array.isArray(res) ? res : res.out
  const room = res.slack == null || !Number.isFinite(res.slack) ? '' : ` (${res.slack.toFixed(0)}px free below)`
  if (list.length) {
    problems += list.length
    console.log(`slide ${n}:${room}`)
    for (const r of list) console.log(`  - ${r}`)
  }
  else {
    console.log(`slide ${n}: ok${room}`)
  }
}
// Exercise every deliberate reveal in the deck, retaining each visual state.
for (const [n, clicks] of [[5,2],[10,1],[12,3],[20,1]]) {
  await page.goto(`${BASE}/${n}?clicks=0`, { waitUntil: 'networkidle' })
  for (let c=0;c<=clicks;c++) {
    await page.waitForTimeout(150)
    await page.screenshot({ path: `preview/slide-${String(n).padStart(2,'0')}-click-${c}.png` })
    if(c<clicks) await page.keyboard.press('ArrowRight')
  }
  const finalUrl=page.url()
  if(!finalUrl.includes(`/${n}`) || !finalUrl.includes(`clicks=${clicks}`)) {
    console.log(`slide ${n}: unexpected click navigation ${finalUrl}`); problems++
  }
}
await writeFile('preview/check-result.json', JSON.stringify({slides:count, problems, clickSlides:[5,10,12,20]}, null, 2))
await browser.close()
console.log(problems ? `\n${problems} problem(s) found` : '\nNo overflow found.')
process.exit(problems ? 1 : 0)
