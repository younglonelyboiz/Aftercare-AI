export default async function globalTeardown() {
  try {
    await fetch('http://127.0.0.1:8011/__test/cleanup', { method: 'POST', signal: AbortSignal.timeout(3000) });
  } catch {
    // Startup failure or server shutdown: FastAPI shutdown handler is the fallback cleanup.
  }
}
