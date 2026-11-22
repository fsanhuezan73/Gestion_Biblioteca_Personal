// Genera un video Y4M (formato que Chrome acepta como cámara falsa) con el
// código de barras EAN-13 de un ISBN, dibujado módulo a módulo.
import { Buffer } from 'node:buffer'
import { writeFileSync } from 'node:fs'

const L = ['0001101', '0011001', '0010011', '0111101', '0100011', '0110001', '0101111', '0111011', '0110111', '0001011']
const R = L.map((c) => [...c].map((b) => (b === '0' ? '1' : '0')).join(''))
const G = R.map((c) => [...c].reverse().join(''))
const PARITY = ['LLLLLL', 'LLGLGG', 'LLGGLG', 'LLGGGL', 'LGLLGG', 'LGGLLG', 'LGGGLL', 'LGLGLG', 'LGLGGL', 'LGGLGL']

export function ean13Modules(code) {
  const d = [...code].map(Number)
  const parity = PARITY[d[0]]
  let bits = '101'
  for (let i = 1; i <= 6; i++) bits += (parity[i - 1] === 'L' ? L : G)[d[i]]
  bits += '01010'
  for (let i = 7; i <= 12; i++) bits += R[d[i]]
  return bits + '101'
}

export function writeBarcodeY4m(path, code, { width = 640, height = 480, frames = 2 } = {}) {
  const modules = ean13Modules(code)
  const moduleWidth = 4
  const barsWidth = modules.length * moduleWidth
  const left = Math.floor((width - barsWidth) / 2)
  const top = Math.floor(height * 0.3)
  const bottom = Math.floor(height * 0.7)

  const y = Buffer.alloc(width * height, 235) // fondo blanco (luma de video)
  for (let row = top; row < bottom; row++) {
    for (let m = 0; m < modules.length; m++) {
      if (modules[m] !== '1') continue
      y.fill(16, row * width + left + m * moduleWidth, row * width + left + (m + 1) * moduleWidth)
    }
  }
  const chroma = Buffer.alloc((width / 2) * (height / 2), 128)
  const frame = Buffer.concat([Buffer.from('FRAME\n'), y, chroma, chroma])
  const header = Buffer.from(`YUV4MPEG2 W${width} H${height} F10:1 Ip A1:1 C420jpeg\n`)
  writeFileSync(path, Buffer.concat([header, ...Array(frames).fill(frame)]))
  return path
}
