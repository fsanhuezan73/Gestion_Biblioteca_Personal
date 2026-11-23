// Preparación de imágenes de portada antes de subirlas.

export const MAX_SOURCE_BYTES = 10 * 1024 * 1024 // archivo original elegido por el usuario
export const MAX_UPLOAD_BYTES = 2 * 1024 * 1024 // límite del backend
export const COVER_MAX_SIDE = 800
export const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp']

// Error con un mensaje listo para mostrar en la interfaz.
export class CoverImageError extends Error {}

export function validateCoverFile(file) {
  if (!file) throw new CoverImageError('No se seleccionó ninguna imagen.')
  // iPhone entrega fotos HEIC: el navegador suele convertirlas; si no, se avisa.
  if (file.type && !file.type.startsWith('image/')) {
    throw new CoverImageError('El archivo no es una imagen. Usa JPG, PNG o WebP.')
  }
  if (file.size > MAX_SOURCE_BYTES) {
    throw new CoverImageError('La imagen supera los 10 MB. Elige una más liviana.')
  }
}

// Tamaño final manteniendo la proporción; nunca agranda la imagen.
export function fitWithin(width, height, maxSide = COVER_MAX_SIDE) {
  const scale = Math.min(1, maxSide / Math.max(width, height))
  return { width: Math.max(1, Math.round(width * scale)), height: Math.max(1, Math.round(height * scale)) }
}

async function decode(file) {
  if (globalThis.createImageBitmap) {
    // imageOrientation respeta la rotación EXIF de las fotos del celular.
    return globalThis.createImageBitmap(file, { imageOrientation: 'from-image' })
  }
  const url = globalThis.URL.createObjectURL(file)
  try {
    const img = new globalThis.Image()
    img.src = url
    await img.decode()
    return img
  } finally {
    globalThis.URL.revokeObjectURL(url)
  }
}

// Redimensiona a COVER_MAX_SIDE y convierte a JPEG (fondo blanco para PNG transparentes).
export async function compressCoverImage(file, { maxSide = COVER_MAX_SIDE, quality = 0.85 } = {}) {
  validateCoverFile(file)
  let source
  try {
    source = await decode(file)
  } catch {
    throw new CoverImageError('No se pudo leer la imagen. Prueba con un archivo JPG o PNG.')
  }
  const { width, height } = fitWithin(source.width, source.height, maxSide)
  const canvas = globalThis.document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, width, height)
  ctx.drawImage(source, 0, 0, width, height)
  source.close?.()

  const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', quality))
  if (!blob) throw new CoverImageError('No se pudo procesar la imagen.')
  if (blob.size > MAX_UPLOAD_BYTES) throw new CoverImageError('La imagen sigue siendo demasiado grande.')
  return blob
}
