import { afterEach, describe, expect, it, vi } from 'vitest'
import { CoverImageError, compressCoverImage, fitWithin, validateCoverFile } from './images'

const file = (type, size = 1000) => ({ type, size, name: 'portada' })

describe('validateCoverFile', () => {
  it('acepta imágenes de hasta 10 MB', () => {
    expect(() => validateCoverFile(file('image/jpeg', 10 * 1024 * 1024))).not.toThrow()
    expect(() => validateCoverFile(file('image/heic'))).not.toThrow()
  })

  it('rechaza archivos que no son imágenes o son muy grandes', () => {
    expect(() => validateCoverFile(file('application/pdf'))).toThrow(CoverImageError)
    expect(() => validateCoverFile(file('image/png', 10 * 1024 * 1024 + 1))).toThrow('10 MB')
    expect(() => validateCoverFile(null)).toThrow(CoverImageError)
  })
})

describe('fitWithin', () => {
  it('reduce manteniendo la proporción', () => {
    expect(fitWithin(1600, 2400)).toEqual({ width: 533, height: 800 })
    expect(fitWithin(3000, 1000, 600)).toEqual({ width: 600, height: 200 })
  })

  it('nunca agranda imágenes pequeñas', () => {
    expect(fitWithin(300, 450)).toEqual({ width: 300, height: 450 })
  })
})

describe('compressCoverImage', () => {
  afterEach(() => vi.unstubAllGlobals())

  function stubCanvas(blob) {
    const ctx = { fillRect: vi.fn(), drawImage: vi.fn(), fillStyle: '' }
    const canvas = { getContext: () => ctx, toBlob: vi.fn((cb, type, quality) => cb(blob && { ...blob, type, quality })) }
    vi.spyOn(document, 'createElement').mockReturnValue(canvas)
    return { canvas, ctx }
  }

  it('redimensiona y convierte a JPEG', async () => {
    const bitmap = { width: 1200, height: 1800, close: vi.fn() }
    vi.stubGlobal('createImageBitmap', vi.fn().mockResolvedValue(bitmap))
    const { canvas, ctx } = stubCanvas({ size: 90_000 })

    const result = await compressCoverImage(file('image/png'))

    expect(canvas.width).toBe(533)
    expect(canvas.height).toBe(800)
    expect(ctx.fillRect).toHaveBeenCalled() // fondo blanco para PNG transparentes
    expect(ctx.drawImage).toHaveBeenCalledWith(bitmap, 0, 0, 533, 800)
    expect(result).toMatchObject({ type: 'image/jpeg', quality: 0.85 })
    expect(bitmap.close).toHaveBeenCalled()
  })

  it('muestra un error legible si la imagen no se puede leer', async () => {
    vi.stubGlobal('createImageBitmap', vi.fn().mockRejectedValue(new Error('decode')))
    await expect(compressCoverImage(file('image/heic'))).rejects.toThrow('No se pudo leer la imagen')
  })

  it('rechaza el resultado si supera el límite del backend', async () => {
    vi.stubGlobal('createImageBitmap', vi.fn().mockResolvedValue({ width: 800, height: 800 }))
    stubCanvas({ size: 3 * 1024 * 1024 })
    await expect(compressCoverImage(file('image/jpeg'))).rejects.toThrow(CoverImageError)
  })
})
