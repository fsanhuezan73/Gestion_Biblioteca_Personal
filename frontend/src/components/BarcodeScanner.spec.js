import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const detect = vi.fn()
vi.mock('@/utils/barcode', async (importOriginal) => ({
  ...(await importOriginal()),
  getIsbnDetector: vi.fn(async () => ({ detect })),
}))

import BarcodeScanner from './BarcodeScanner.vue'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
let track

function fakeCamera({ fail } = {}) {
  track = {
    stop: vi.fn(),
    getSettings: () => ({ deviceId: 'back' }),
    getCapabilities: () => ({ torch: true }),
    applyConstraints: vi.fn(async () => {}),
  }
  const stream = { getTracks: () => [track], getVideoTracks: () => [track] }
  Object.defineProperty(globalThis.navigator, 'mediaDevices', {
    configurable: true,
    value: {
      getUserMedia: fail ? vi.fn(async () => { throw Object.assign(new Error('x'), { name: fail }) }) : vi.fn(async () => stream),
      enumerateDevices: vi.fn(async () => [
        { kind: 'videoinput', deviceId: 'back' }, { kind: 'videoinput', deviceId: 'front' },
      ]),
    },
  })
}

beforeEach(() => {
  detect.mockReset()
  globalThis.isSecureContext = true
  vi.spyOn(globalThis.HTMLMediaElement.prototype, 'play').mockResolvedValue()
  vi.spyOn(globalThis.HTMLMediaElement.prototype, 'readyState', 'get').mockReturnValue(4)
  Object.defineProperty(globalThis.navigator, 'vibrate', { configurable: true, value: vi.fn() })
})
afterEach(() => vi.restoreAllMocks())

describe('BarcodeScanner', () => {
  it('detecta un ISBN, vibra, apaga la cámara y lo emite', async () => {
    fakeCamera()
    detect.mockResolvedValueOnce([]).mockResolvedValue([{ rawValue: '9780451524935' }])
    const wrapper = mount(BarcodeScanner)
    await flushPromises()
    await sleep(400)
    expect(wrapper.emitted('detected')).toEqual([['9780451524935']])
    expect(track.stop).toHaveBeenCalled()
    expect(globalThis.navigator.vibrate).toHaveBeenCalled()
  })

  it('ignora códigos que no son de libros y sigue escaneando', async () => {
    fakeCamera()
    detect.mockResolvedValue([{ rawValue: '9771234567003' }])
    const wrapper = mount(BarcodeScanner)
    await flushPromises()
    await sleep(400)
    expect(wrapper.emitted('detected')).toBeUndefined()
    expect(wrapper.find('[data-test="scanner-notice"]').text()).toContain('no corresponde a un libro')
    expect(detect.mock.calls.length).toBeGreaterThan(1)
    wrapper.unmount()
    expect(track.stop).toHaveBeenCalled()
  })

  it('muestra controles de cámara y linterna', async () => {
    fakeCamera()
    detect.mockResolvedValue([])
    const wrapper = mount(BarcodeScanner)
    await flushPromises()
    expect(wrapper.find('[data-test="switch-camera"]').exists()).toBe(true)
    await wrapper.find('[data-test="toggle-torch"]').trigger('click')
    await flushPromises()
    expect(track.applyConstraints).toHaveBeenCalledWith({ advanced: [{ torch: true }] })
    expect(wrapper.find('[data-test="toggle-torch"]').text()).toContain('Apagar linterna')
    wrapper.unmount()
  })

  it('explica el permiso denegado y mantiene la opción de foto', async () => {
    fakeCamera({ fail: 'NotAllowedError' })
    const wrapper = mount(BarcodeScanner)
    await flushPromises()
    expect(wrapper.find('[data-test="camera-error"]').text()).toContain('No diste permiso')
    expect(wrapper.find('[data-test="photo-input"]').exists()).toBe(true)
  })

  it('lee el código desde una foto', async () => {
    fakeCamera({ fail: 'NotFoundError' })
    globalThis.createImageBitmap = vi.fn(async () => ({ close: vi.fn() }))
    detect.mockResolvedValue([{ rawValue: '9780306406157' }])
    const wrapper = mount(BarcodeScanner)
    await flushPromises()
    const input = wrapper.find('[data-test="photo-input"]')
    Object.defineProperty(input.element, 'files', { value: [new globalThis.File(['x'], 'codigo.jpg')] })
    await input.trigger('change')
    await flushPromises()
    expect(wrapper.emitted('detected')).toEqual([['9780306406157']])
  })

  it('Cancelar cierra y libera la cámara', async () => {
    fakeCamera()
    detect.mockResolvedValue([])
    const wrapper = mount(BarcodeScanner)
    await flushPromises()
    await wrapper.findAll('button').find((b) => b.text() === 'Cancelar').trigger('click')
    expect(wrapper.emitted('close')).toHaveLength(1)
    expect(track.stop).toHaveBeenCalled()
  })
})
