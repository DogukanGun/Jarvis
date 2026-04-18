const windowApi = (window as unknown as { api?: {
  biometricAvailable?: () => Promise<boolean>
  biometricVerify?: (reason: string) => Promise<boolean>
} }).api

export async function isBiometricAvailable(): Promise<boolean> {
  if (!windowApi?.biometricAvailable) return false
  try {
    return await windowApi.biometricAvailable()
  } catch {
    return false
  }
}

export async function verify(reason = 'Verify your identity'): Promise<boolean> {
  if (!windowApi?.biometricVerify) return false
  try {
    return await windowApi.biometricVerify(reason)
  } catch {
    return false
  }
}
