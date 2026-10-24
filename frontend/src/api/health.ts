export interface HealthResponse {
  status: 'ok'
}

function isHealthResponse(value: unknown): value is HealthResponse {
  return (
    typeof value === 'object' &&
    value !== null &&
    (value as { status?: unknown }).status === 'ok'
  )
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch('/health')
  if (!response.ok) {
    throw new Error(`GET /health respondeu ${response.status}`)
  }
  const body: unknown = await response.json()
  if (!isHealthResponse(body)) {
    throw new Error('GET /health devolveu um corpo inesperado')
  }
  return body
}
