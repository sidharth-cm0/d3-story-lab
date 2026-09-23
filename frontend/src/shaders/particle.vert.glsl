/**
 * particle.vert.glsl
 * D3 Story Lab — Dark Granular Point-Cloud Vertex Shader
 *
 * Core Metaphor:
 * - Continuous undulating wave deformation (Narrative Probability Terrain)
 * - Morphing between ambient dispersion and agent silhouettes (Emergence)
 * - Distance attenuation for cinematic depth
 */

uniform float uTime;
uniform float uProgress;
uniform float uDensity;
uniform float uPointSize;
uniform float uOpacity;
uniform float uMorph;
uniform float uDepthFade;
uniform float uAmberBoost;
uniform float uPixelRatio;

attribute vec3 aTarget;
attribute vec3 aColor;
attribute float aSize;
attribute float aPhase;
attribute float aLayerId;

varying vec3 vColor;
varying float vLayerId;
varying float vAlpha;
varying float vDistToCam;

void main() {
  vLayerId = aLayerId;
  vColor = aColor;

  // 1. Morph between initial terrain/dispersion and coherent target structure
  float morphClamped = clamp(uMorph, 0.0, 1.0);
  vec3 morphedPos = mix(position, aTarget, morphClamped);

  // 2. Procedural harmonic wave displacement (narrative probability field)
  // Subtle undulation that scales with depth and layer
  float waveIntensity = (aLayerId < 1.5) ? 0.28 : 0.08;
  float waveY = sin(uTime * 0.75 + morphedPos.x * 0.35 + aPhase) *
                cos(uTime * 0.55 + morphedPos.z * 0.28 + aPhase * 0.7) * waveIntensity;

  // Layer 3 (Causal Transference Stream) pulses along its arc
  if (aLayerId > 2.5 && aLayerId < 3.5) {
    waveY += sin(uTime * 2.2 + morphedPos.x * 1.5) * 0.07;
  }

  vec3 finalPos = morphedPos + vec3(0.0, waveY, 0.0);

  // 3. Staged resolve appearance
  float layerStagedEntrance = clamp((uProgress * 4.0) - (aLayerId * 0.55), 0.0, 1.0);
  finalPos.y *= layerStagedEntrance;

  // 4. ModelView and Projection
  vec4 mvPosition = modelViewMatrix * vec4(finalPos, 1.0);
  gl_Position = projectionMatrix * mvPosition;

  // 5. Distance to camera for depth fog calculation
  vDistToCam = -mvPosition.z;

  // 6. Distance-attenuated point size (forensic precision)
  float basePtSize = aSize * uPointSize * uPixelRatio;
  // Boost points slightly on hover
  basePtSize *= (1.0 + uAmberBoost * 0.15);

  gl_PointSize = basePtSize * (260.0 / max(vDistToCam, 1.0));
  gl_PointSize = clamp(gl_PointSize, 1.0, 14.0);

  // 7. Base alpha calculation
  vAlpha = uOpacity * layerStagedEntrance;
}
