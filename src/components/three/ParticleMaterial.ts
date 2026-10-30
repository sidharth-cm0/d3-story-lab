/**
 * ParticleMaterial.ts
 *
 * Three.js ShaderMaterial factory for D3 Story Lab's granular point-cloud.
 * Provides custom GLSL shaders with uniforms for wave deformation, morphing,
 * distance attenuation, circular Gaussian falloff, and D3 amber accentuation.
 */

import * as THREE from 'three';

export interface ParticleUniforms {
  uTime: { value: number };
  uProgress: { value: number };
  uDensity: { value: number };
  uPointSize: { value: number };
  uOpacity: { value: number };
  uMorph: { value: number };
  uDepthFade: { value: number };
  uAmberBoost: { value: number };
  uPixelRatio: { value: number };
}

export const granularVertexShader = `
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

  // Morph between initial terrain/dispersion and coherent target structure
  float morphClamped = clamp(uMorph, 0.0, 1.0);
  vec3 morphedPos = mix(position, aTarget, morphClamped);

  // Procedural harmonic wave displacement (narrative probability field)
  float waveIntensity = (aLayerId < 1.5) ? 0.28 : 0.08;
  float waveY = sin(uTime * 0.75 + morphedPos.x * 0.35 + aPhase) *
                cos(uTime * 0.55 + morphedPos.z * 0.28 + aPhase * 0.7) * waveIntensity;

  if (aLayerId > 2.5 && aLayerId < 3.5) {
    waveY += sin(uTime * 2.2 + morphedPos.x * 1.5) * 0.07;
  }

  vec3 finalPos = morphedPos + vec3(0.0, waveY, 0.0);

  // Staged resolve appearance
  float layerStagedEntrance = clamp((uProgress * 4.0) - (aLayerId * 0.55), 0.0, 1.0);
  finalPos.y *= layerStagedEntrance;

  vec4 mvPosition = modelViewMatrix * vec4(finalPos, 1.0);
  gl_Position = projectionMatrix * mvPosition;

  vDistToCam = -mvPosition.z;

  float basePtSize = aSize * uPointSize * uPixelRatio;
  basePtSize *= (1.0 + uAmberBoost * 0.15);

  gl_PointSize = basePtSize * (260.0 / max(vDistToCam, 1.0));
  gl_PointSize = clamp(gl_PointSize, 1.0, 14.0);

  vAlpha = uOpacity * layerStagedEntrance;
}
`;

export const granularFragmentShader = `
uniform float uDepthFade;
uniform float uAmberBoost;

varying vec3 vColor;
varying float vLayerId;
varying float vAlpha;
varying float vDistToCam;

void main() {
  vec2 coord = gl_PointCoord - vec2(0.5);
  float dist = length(coord);

  if (dist > 0.5) {
    discard;
  }

  float radialSoftness = smoothstep(0.5, 0.06, dist);
  float depthFactor = exp(-0.0018 * vDistToCam * vDistToCam * uDepthFade);
  depthFactor = clamp(depthFactor, 0.12, 1.0);

  vec3 finalColor = vColor;
  if (vLayerId > 2.5) {
    vec3 d3Amber = vec3(0.83, 0.68, 0.22);
    finalColor = mix(finalColor, d3Amber, clamp(uAmberBoost * 0.45 + 0.35, 0.0, 1.0));
  } else if (uAmberBoost > 0.01) {
    vec3 warmAmberTint = vec3(0.95, 0.88, 0.70);
    finalColor = mix(finalColor, warmAmberTint, uAmberBoost * 0.15);
  }

  float finalAlpha = vAlpha * radialSoftness * depthFactor;
  if (finalAlpha < 0.015) {
    discard;
  }

  gl_FragColor = vec4(finalColor, finalAlpha);
}
`;

export function createParticleMaterial(initialUniforms?: Partial<ParticleUniforms>): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    vertexShader: granularVertexShader,
    fragmentShader: granularFragmentShader,
    uniforms: {
      uTime: { value: 0.0 },
      uProgress: { value: 0.0 },
      uDensity: { value: 1.0 },
      uPointSize: { value: 1.0 },
      uOpacity: { value: 0.0 },
      uMorph: { value: 0.0 },
      uDepthFade: { value: 1.0 },
      uAmberBoost: { value: 0.0 },
      uPixelRatio: { value: typeof window !== 'undefined' ? Math.min(window.devicePixelRatio || 1, 1.5) : 1 },
      ...initialUniforms,
    },
    transparent: true,
    depthWrite: false,
    blending: THREE.NormalBlending,
  });
}
