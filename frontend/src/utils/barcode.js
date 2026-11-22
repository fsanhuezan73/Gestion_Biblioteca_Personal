// Lector de códigos de barras. Se importa de forma diferida (solo al abrir el
// escáner) para no aumentar el peso de la app.
//
// Usa el BarcodeDetector nativo del navegador si soporta EAN-13 (Chrome en
// Android); si no (Safari/iPhone, Firefox, escritorio), usa ZXing compilado a
// WebAssembly, servido desde la propia app (sin CDN externo).

let detectorPromise = null

async function createDetector() {
  const Native = globalThis.BarcodeDetector
  if (Native?.getSupportedFormats) {
    try {
      const formats = await Native.getSupportedFormats()
      if (formats.includes('ean_13')) return new Native({ formats: ['ean_13'] })
    } catch { /* se usa el lector WebAssembly */ }
  }

  const [{ BarcodeDetector, prepareZXingModule }, { default: wasmUrl }] = await Promise.all([
    import('barcode-detector/ponyfill'),
    import('zxing-wasm/reader/zxing_reader.wasm?url'),
  ])
  prepareZXingModule({
    overrides: {
      locateFile: (path, prefix) => (path.endsWith('.wasm') ? wasmUrl : prefix + path),
    },
  })
  return new BarcodeDetector({ formats: ['ean_13'] })
}

/** Detector compartido (se crea una sola vez por sesión). */
export function getIsbnDetector() {
  if (!detectorPromise) {
    detectorPromise = createDetector().catch((err) => {
      detectorPromise = null
      throw err
    })
  }
  return detectorPromise
}

/** Mensaje claro para los errores de getUserMedia. */
export function cameraErrorMessage(error) {
  if (!globalThis.isSecureContext) {
    return 'La cámara solo está disponible en conexiones seguras (HTTPS).'
  }
  switch (error?.name) {
    case 'NotAllowedError':
    case 'SecurityError':
      return 'No diste permiso para usar la cámara. Actívalo en la configuración del navegador para este sitio, o sube una foto del código.'
    case 'NotFoundError':
    case 'OverconstrainedError':
      return 'No se encontró una cámara en este dispositivo. Puedes subir una foto del código.'
    case 'NotReadableError':
      return 'La cámara está siendo usada por otra aplicación. Ciérrala e intenta nuevamente.'
    default:
      return 'No se pudo iniciar la cámara. Puedes subir una foto del código o escribir el ISBN.'
  }
}
