// All application requests use one transport policy: same-origin cookies,
// caller-provided cancellation/cache/headers, and no automatic retry.
// Endpoint clients keep ownership of response parsing and error classification.
export function apiFetch(
  path: string,
  init: Omit<RequestInit, 'credentials'> = {},
): Promise<Response> {
  return fetch(path, { ...init, credentials: 'same-origin' })
}

// Invalid or empty JSON is untrusted. Endpoint clients decide what it means.
export async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    return null
  }
}
