<template>
  <div
    class="modal d-block scanner-backdrop"
    tabindex="-1"
    role="dialog"
    aria-modal="true"
    aria-labelledby="scanner-title"
    @click.self="close"
    @keydown.esc="close"
  >
    <div class="modal-dialog modal-dialog-centered" role="document">
      <div class="modal-content">
        <div class="modal-header border-0 pb-0">
          <h5 id="scanner-title" class="modal-title fw-bold">Escanear código de barras</h5>
          <button ref="closeButton" type="button" class="btn-close" aria-label="Cerrar" @click="close" />
        </div>

        <div class="modal-body">
          <!-- Vista de cámara -->
          <div v-if="cameraSupported && !cameraError" class="scanner-viewport mb-3">
            <video ref="video" class="scanner-video" muted playsinline autoplay aria-label="Vista de la cámara" />
            <div class="scanner-guide" aria-hidden="true"><span class="scanner-line" /></div>
            <div v-if="starting" class="scanner-overlay">
              <div class="spinner-border text-light" role="status"><span class="visually-hidden">Iniciando cámara…</span></div>
            </div>
          </div>

          <p v-if="!cameraError" class="text-muted small text-center mb-2">
            Centra el código de barras de la contraportada dentro del recuadro.
          </p>

          <div v-if="cameraError" class="alert alert-warning small" role="alert" data-test="camera-error">
            {{ cameraError }}
          </div>
          <div v-if="notice" class="alert alert-info small py-2" role="status" data-test="scanner-notice">
            {{ notice }}
          </div>

          <div class="d-flex flex-wrap gap-2 justify-content-center">
            <button
              v-if="cameras.length > 1 && !cameraError"
              type="button"
              class="btn btn-outline-secondary btn-sm"
              data-test="switch-camera"
              @click="switchCamera"
            >
              🔄 Cambiar cámara
            </button>
            <button
              v-if="torchSupported && !cameraError"
              type="button"
              class="btn btn-outline-secondary btn-sm"
              :aria-pressed="torchOn"
              data-test="toggle-torch"
              @click="toggleTorch"
            >
              🔦 {{ torchOn ? 'Apagar linterna' : 'Linterna' }}
            </button>
            <label class="btn btn-outline-primary btn-sm mb-0" :class="{ disabled: readingPhoto }">
              <span v-if="readingPhoto" class="spinner-border spinner-border-sm me-1" />
              📷 Subir foto del código
              <input
                type="file"
                accept="image/*"
                capture="environment"
                class="visually-hidden"
                data-test="photo-input"
                :disabled="readingPhoto"
                @change="handlePhoto"
              />
            </label>
          </div>
        </div>

        <div class="modal-footer border-0 pt-0">
          <button type="button" class="btn btn-outline-secondary" @click="close">Cancelar</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { cameraErrorMessage, getIsbnDetector } from '@/utils/barcode'
import { isbnFromBarcode } from '@/utils/isbn'

const emit = defineEmits(['detected', 'close'])

const SCAN_INTERVAL_MS = 150
const NOT_A_BOOK = 'Este código no corresponde a un libro. Busca el código que empieza con 978 o 979.'

const video = ref(null)
const closeButton = ref(null)
const cameraSupported = ref(Boolean(globalThis.navigator.mediaDevices?.getUserMedia))
const cameraError = ref(cameraSupported.value ? '' : cameraErrorMessage(null))
const starting = ref(false)
const notice = ref('')
const cameras = ref([])
const torchSupported = ref(false)
const torchOn = ref(false)
const readingPhoto = ref(false)

let stream = null
let detector = null
let timer = null
let cameraIndex = -1
let finished = false

function stopCamera() {
  clearTimeout(timer)
  timer = null
  stream?.getTracks().forEach((track) => track.stop())
  stream = null
  torchOn.value = false
}

async function startCamera(deviceId) {
  stopCamera()
  starting.value = true
  try {
    stream = await globalThis.navigator.mediaDevices.getUserMedia({
      audio: false,
      video: deviceId
        ? { deviceId: { exact: deviceId } }
        : { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } },
    })
    if (finished) return stopCamera()
    await nextTick()
    video.value.srcObject = stream
    await video.value.play().catch(() => {})

    // Con el permiso concedido ya se conocen las cámaras disponibles.
    const devices = await globalThis.navigator.mediaDevices.enumerateDevices?.() ?? []
    cameras.value = devices.filter((d) => d.kind === 'videoinput')
    const track = stream.getVideoTracks()[0]
    const activeId = track?.getSettings?.().deviceId
    cameraIndex = Math.max(0, cameras.value.findIndex((d) => d.deviceId === activeId))
    torchSupported.value = Boolean(track?.getCapabilities?.().torch)

    scheduleScan()
  } catch (error) {
    stopCamera()
    cameraError.value = cameraErrorMessage(error)
  } finally {
    starting.value = false
  }
}

function scheduleScan() {
  timer = setTimeout(scanFrame, SCAN_INTERVAL_MS)
}

async function scanFrame() {
  if (finished || !stream) return
  try {
    if (video.value?.readyState >= 2) {
      const codes = await detector.detect(video.value)
      if (handleCodes(codes)) return
    }
  } catch { /* fotograma ilegible: se intenta con el siguiente */ }
  if (!finished && stream) scheduleScan()
}

/** true si se encontró un ISBN válido (y se cerró el escáner). */
function handleCodes(codes) {
  if (!codes?.length) return false
  for (const code of codes) {
    const isbn = isbnFromBarcode(code.rawValue)
    if (isbn) {
      finish(isbn)
      return true
    }
  }
  notice.value = NOT_A_BOOK
  return false
}

function finish(isbn) {
  finished = true
  stopCamera()
  globalThis.navigator.vibrate?.(80)
  emit('detected', isbn)
}

function close() {
  finished = true
  stopCamera()
  emit('close')
}

async function switchCamera() {
  if (cameras.value.length < 2) return
  cameraIndex = (cameraIndex + 1) % cameras.value.length
  await startCamera(cameras.value[cameraIndex].deviceId)
}

async function toggleTorch() {
  const track = stream?.getVideoTracks()[0]
  if (!track) return
  try {
    await track.applyConstraints({ advanced: [{ torch: !torchOn.value }] })
    torchOn.value = !torchOn.value
  } catch {
    torchSupported.value = false
  }
}

async function handlePhoto(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  readingPhoto.value = true
  notice.value = ''
  try {
    detector ??= await getIsbnDetector()
    const bitmap = await globalThis.createImageBitmap(file)
    const codes = await detector.detect(bitmap)
    bitmap.close?.()
    if (!handleCodes(codes) && !codes.length) {
      notice.value = 'No se encontró un código de barras en la foto. Intenta con una foto más cercana y nítida.'
    }
  } catch {
    notice.value = 'No se pudo leer la foto. Intenta con otra imagen o escribe el ISBN.'
  } finally {
    readingPhoto.value = false
  }
}

onMounted(async () => {
  closeButton.value?.focus()
  try {
    detector = await getIsbnDetector()
  } catch {
    cameraError.value = 'No se pudo cargar el lector de códigos. Revisa tu conexión o escribe el ISBN.'
    return
  }
  if (cameraSupported.value && !finished) await startCamera()
})

onBeforeUnmount(() => {
  finished = true
  stopCamera()
})

defineExpose({ handleCodes })
</script>

<style scoped>
.scanner-backdrop {
  background: rgba(0, 0, 0, 0.6);
}
.scanner-viewport {
  position: relative;
  overflow: hidden;
  border-radius: 0.75rem;
  background: #000;
  aspect-ratio: 4 / 3;
}
.scanner-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.scanner-guide {
  position: absolute;
  inset: 30% 10%;
  border: 3px solid rgba(255, 255, 255, 0.9);
  border-radius: 0.5rem;
  box-shadow: 0 0 0 100vmax rgba(0, 0, 0, 0.35);
}
.scanner-line {
  position: absolute;
  left: 4%;
  right: 4%;
  top: 50%;
  height: 2px;
  background: #ff4d4f;
  animation: scan 1.6s ease-in-out infinite alternate;
}
@keyframes scan {
  from { transform: translateY(-28px); }
  to { transform: translateY(28px); }
}
@media (prefers-reduced-motion: reduce) {
  .scanner-line { animation: none; }
}
.scanner-overlay {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  background: rgba(0, 0, 0, 0.4);
}
</style>
