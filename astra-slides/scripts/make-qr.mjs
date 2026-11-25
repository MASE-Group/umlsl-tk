// Generate the repository QR code locally (no web service).
// Run: npm run qr
import QRCode from 'qrcode'
import { fileURLToPath } from 'node:url'

const url = 'https://github.com/MASE-Group/umlsl-tk'
const out = fileURLToPath(new URL('../public/qr-umlsl-tk.png', import.meta.url))

await QRCode.toFile(out, url, {
  type: 'png',
  width: 800,
  margin: 4,
  errorCorrectionLevel: 'M',
  color: { dark: '#002D4CFF', light: '#FFFFFFFF' }, // KIT royal blue on white
})
console.log(`QR code for ${url} -> ${out}`)
