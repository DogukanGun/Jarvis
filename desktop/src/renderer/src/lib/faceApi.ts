const BASE = 'http://localhost:8400'

export async function adminExists(): Promise<boolean> {
  const res = await fetch(`${BASE}/api/admin/exists`)
  const data = (await res.json()) as { exists: boolean }
  return data.exists
}

export async function enrollAdmin(imageBase64: string): Promise<{ success?: boolean; error?: string }> {
  const res = await fetch(`${BASE}/api/admin/enroll`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image: imageBase64 }),
  })
  return res.json()
}

export async function verifyAdmin(
  imageBase64: string,
): Promise<{ success?: boolean; data?: boolean; error?: string }> {
  const res = await fetch(`${BASE}/api/admin/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image: imageBase64 }),
  })
  return res.json()
}
