export function newPasswordError(password) {
  if (password.length < 8) return 'La contraseña debe tener al menos 8 caracteres'
  if (new globalThis.Blob([password]).size > 72) return 'La contraseña no puede superar 72 bytes en UTF-8'
  return ''
}
