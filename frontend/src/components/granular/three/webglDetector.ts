/**
 * webglDetector.ts
 *
 * Safe WebGL capability detection for D3 Story Lab (Phase 9.2.7).
 * Avoids crashing in JSDOM / headless test environments or browsers without WebGL.
 */

let cachedSupport: boolean | null = null;

export function isWebGLAvailable(): boolean {
  if (cachedSupport !== null) {
    return cachedSupport;
  }

  // JSDOM / SSR check
  if (typeof window === 'undefined' || typeof document === 'undefined') {
    cachedSupport = false;
    return false;
  }

  // Fast check: if neither WebGLRenderingContext nor WebGL2RenderingContext exists on window, return false
  if (
    typeof (window as any).WebGLRenderingContext === 'undefined' &&
    typeof (window as any).WebGL2RenderingContext === 'undefined'
  ) {
    cachedSupport = false;
    return false;
  }

  try {
    const canvas = document.createElement('canvas');
    const gl =
      canvas.getContext('webgl2') ||
      canvas.getContext('webgl') ||
      canvas.getContext('experimental-webgl');

    cachedSupport = !!(gl && typeof (gl as WebGLRenderingContext).getExtension === 'function');
    return cachedSupport;
  } catch {
    cachedSupport = false;
    return false;
  }
}

/**
 * Allows test suites to override WebGL availability detection for testing fallbacks.
 */
export function setMockWebGLAvailable(available: boolean | null): void {
  cachedSupport = available;
}
