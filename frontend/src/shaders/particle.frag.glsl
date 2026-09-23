/**
 * particle.frag.glsl
 * D3 Story Lab — Dark Granular Point-Cloud Fragment Shader
 *
 * Core Aesthetic:
 * - Soft circular particles with Gaussian radial falloff (no square billboards)
 * - Filmic dark monochrome palette (warm off-white, graphite, muted gray)
 * - Restrained D3 amber/gold accents on causal streams and turning nodes
 * - Smooth exponential depth fade
 */

uniform float uDepthFade;
uniform float uAmberBoost;

varying vec3 vColor;
varying float vLayerId;
varying float vAlpha;
varying float vDistToCam;

void main() {
  // 1. Calculate circular distance from point center
  vec2 coord = gl_PointCoord - vec2(0.5);
  float dist = length(coord);

  // Discard fragments outside circle to prevent square bounding artifacts
  if (dist > 0.5) {
    discard;
  }

  // 2. Gaussian-like soft falloff: crisp core with gentle particulate edge
  float radialSoftness = smoothstep(0.5, 0.06, dist);

  // 3. Exponential depth fade (atmospheric fog)
  float depthFactor = exp(-0.0018 * vDistToCam * vDistToCam * uDepthFade);
  depthFactor = clamp(depthFactor, 0.12, 1.0);

  // 4. Color grading: selective amber boost on hover and causal streams
  vec3 finalColor = vColor;
  if (vLayerId > 2.5) {
    // Causal Stream / Focal Nodes
    vec3 d3Amber = vec3(0.83, 0.68, 0.22); // #D4AF37
    finalColor = mix(finalColor, d3Amber, clamp(uAmberBoost * 0.45 + 0.35, 0.0, 1.0));
  } else if (uAmberBoost > 0.01) {
    // Subtle overall warmth on hover
    vec3 warmAmberTint = vec3(0.95, 0.88, 0.70);
    finalColor = mix(finalColor, warmAmberTint, uAmberBoost * 0.15);
  }

  // 5. Compute final particle opacity
  float finalAlpha = vAlpha * radialSoftness * depthFactor;

  if (finalAlpha < 0.015) {
    discard;
  }

  gl_FragColor = vec4(finalColor, finalAlpha);
}
