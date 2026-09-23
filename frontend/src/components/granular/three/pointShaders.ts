/**
 * pointShaders.ts
 *
 * Custom GLSL shaders for D3 Story Lab's Persistent Granular Three.js Environment (Phase 9.2.8).
 *
 * Features:
 * - 8 Distinct Workspace Topologies:
 *   0: HERO (Emergence Iris Ring)
 *   1: WORLD (Topographic Rolling Terrain)
 *   2: ACTORS (Dual-Agent Concentration Field)
 *   3: ARCS (Flowing Narrative Ribbons & Trajectories)
 *   4: SIMULATION (Kinetic Event Energy & Pulse Clusters)
 *   5: SCRIPT (Quiet Peripheral Field with Central Reading Clear)
 *   6: STORYBOARD (Rectangular Cinematic Compositional Frames)
 *   7: EXPORT (Minimal Settled Equilibrium Field)
 * - GPU-driven motif interpolation: uMotifFrom -> uMotifTo via uMotifProgress (0.0 to 1.0).
 * - 3D Simplex & Curl Noise on the GPU.
 * - Circular Gaussian falloff in fragment shader with luminous nucleus.
 * - Restrained palette: --text-primary (#F5F3EF) with subtle flashes of --accent (#C9A46B).
 * - Central reading column clearing for SCRIPT view.
 */

export const granularVertexShader = /* glsl */ `
  attribute vec3 aTarget;
  attribute vec3 aColor;
  attribute float aSize;
  attribute float aPhase;
  attribute float aLayerId;

  uniform float uTime;
  uniform float uProgress;
  uniform float uPointSize;
  uniform float uDepthFade;

  // Motif Transition Uniforms
  uniform float uMotifFrom;
  uniform float uMotifTo;
  uniform float uMotifProgress; // 0.0 -> 1.0
  uniform float uTurbulence;
  uniform float uPointScale;
  uniform float uAccentStrength;
  uniform float uCenterClear;   // 1.0 = pushes particles away from center for Script reading

  varying vec3 vColor;
  varying float vAlpha;
  varying float vDepth;
  varying float vLayerId;
  varying float vAccent;

  // ---------------------------------------------------------------------------
  // Simplex 3D Noise (Ian McEwan, Ashima Arts / Stefan Gustavson)
  // ---------------------------------------------------------------------------
  vec4 permute(vec4 x) { return mod(((x * 34.0) + 1.0) * x, 289.0); }
  vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

  float snoise(vec3 v) {
    const vec2 C = vec2(1.0 / 6.0, 1.0 / 3.0);
    const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);

    vec3 i  = floor(v + dot(v, C.yyy));
    vec3 x0 = v - i + dot(i, C.xxx);

    vec3 g = step(x0.yzx, x0.xyz);
    vec3 l = 1.0 - g;
    vec3 i1 = min(g.xyz, l.zxy);
    vec3 i2 = max(g.xyz, l.zxy);

    vec3 x1 = x0 - i1 + 1.0 * C.xxx;
    vec3 x2 = x0 - i2 + 2.0 * C.xxx;
    vec3 x3 = x0 - 1.0 + 3.0 * C.xxx;

    i = mod(i, 289.0);
    vec4 p = permute(permute(permute(
               i.z + vec4(0.0, i1.z, i2.z, 1.0))
             + i.y + vec4(0.0, i1.y, i2.y, 1.0))
             + i.x + vec4(0.0, i1.x, i2.x, 1.0));

    float n_ = 1.0 / 7.0;
    vec3  ns = n_ * D.wyz - D.xzx;

    vec4 j = p - 49.0 * floor(p * ns.z * ns.z);

    vec4 x_ = floor(j * ns.z);
    vec4 y_ = floor(j - 7.0 * x_);

    vec4 x = x_ * ns.x + ns.yyyy;
    vec4 y = y_ * ns.x + ns.yyyy;
    vec4 h = 1.0 - abs(x) - abs(y);

    vec4 b0 = vec4(x.xy, y.xy);
    vec4 b1 = vec4(x.zw, y.zw);

    vec4 s0 = floor(b0) * 2.0 + 1.0;
    vec4 s1 = floor(b1) * 2.0 + 1.0;
    vec4 sh = -step(h, vec4(0.0));

    vec4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
    vec4 a1 = b1.xzyw + s1.xzyw * sh.zzww;

    vec3 p0 = vec3(a0.xy, h.x);
    vec3 p1 = vec3(a0.zw, h.y);
    vec3 p2 = vec3(a1.xy, h.z);
    vec3 p3 = vec3(a1.zw, h.w);

    vec4 norm = taylorInvSqrt(vec4(dot(p0, p0), dot(p1, p1), dot(p2, p2), dot(p3, p3)));
    p0 *= norm.x;
    p1 *= norm.y;
    p2 *= norm.z;
    p3 *= norm.w;

    vec4 m = max(0.6 - vec4(dot(x0, x0), dot(x1, x1), dot(x2, x2), dot(x3, x3)), 0.0);
    m = m * m;
    return 42.0 * dot(m * m, vec4(dot(p0, x0), dot(p1, x1), dot(p2, x2), dot(p3, x3)));
  }

  // ---------------------------------------------------------------------------
  // 3D Curl Noise using central differences
  // ---------------------------------------------------------------------------
  vec3 curlNoise(vec3 p) {
    const float e = 0.08;
    float n1 = snoise(p + vec3(0.0, e, 0.0));
    float n2 = snoise(p - vec3(0.0, e, 0.0));
    float n3 = snoise(p + vec3(0.0, 0.0, e));
    float n4 = snoise(p - vec3(0.0, 0.0, e));
    float n5 = snoise(p + vec3(e, 0.0, 0.0));
    float n6 = snoise(p - vec3(e, 0.0, 0.0));

    float x = (n1 - n2) - (n3 - n4);
    float y = (n3 - n4) - (n5 - n6);
    float z = (n5 - n6) - (n1 - n2);

    return vec3(x, y, z) / (2.0 * e);
  }

  // ---------------------------------------------------------------------------
  // Procedural Workspace Topology Generator on GPU
  // ---------------------------------------------------------------------------
  vec3 computeMotifPosition(float motifId, vec3 seedPos, float t, vec3 curl) {
    float r = length(seedPos.xy);
    vec2 dir = r > 0.001 ? normalize(seedPos.xy) : vec2(1.0, 0.0);
    vec2 tangent = vec2(-dir.y, dir.x);
    float angle = atan(seedPos.y, seedPos.x);

    // 0: HERO — Volatile Emergence Iris Ring
    if (motifId < 0.5) {
      float wave = sin(angle * 3.0 + t * 1.8 + aPhase) * 0.22 + cos(angle * 6.0 - t * 1.2 + aPhase * 1.5) * 0.12;
      float burstRaw = snoise(vec3(dir * 1.75, t * 0.5 + aPhase * 0.35));
      float burstMag = pow(abs(burstRaw), 2.8) * sign(burstRaw);
      float radialDisplacement = wave + burstMag * 2.4 + curl.x * 0.65;
      float displacedRadius = max(0.35, r + radialDisplacement);
      float gravityPull = (r - displacedRadius) * 0.22;
      float finalRadius = displacedRadius + gravityPull;
      float swirl = curl.y * 0.45 + sin(t * 1.4 + aPhase) * 0.18;
      return vec3(dir * finalRadius + tangent * swirl, seedPos.z + curl.z * 0.55 + sin(angle * 2.0 + t + aPhase) * 0.22);
    }

    // 1: WORLD — Topographic Rolling Terrain
    if (motifId < 1.5) {
      float x = (seedPos.x / 4.0) * 14.0;
      float z = (seedPos.y / 4.0) * 8.0;
      float elev = sin(x * 0.28 + t * 0.4) * 0.95 + cos(z * 0.42 + t * 0.3) * 0.75 + sin(x * 0.65 + z * 0.5) * 0.35;
      float y = -1.2 + elev + curl.y * 0.4;
      return vec3(x, y, z + curl.z * 0.3);
    }

    // 2: ACTORS — Dual-Agent Concentration Field (Left & Right Centroids)
    if (motifId < 2.5) {
      float side = sin(aPhase * 7.0) > 0.0 ? 1.0 : -1.0;
      vec2 center = vec2(side * 4.2, 0.2);
      float clusterR = length(seedPos.xy) * 0.45;
      vec2 p = center + dir * clusterR + curl.xy * 0.35;
      if (aLayerId > 2.5) {
        // Causal bridge between agents
        float bridgeT = fract(aPhase * 3.0 + t * 0.2);
        p = mix(vec2(-4.2, 0.2), vec2(4.2, 0.2), bridgeT) + vec2(0.0, sin(bridgeT * 3.1415) * 1.2) + curl.xy * 0.2;
      }
      return vec3(p, seedPos.z * 0.6 + curl.z * 0.3);
    }

    // 3: ARCS — Flowing Narrative Ribbons & Causality Streams
    if (motifId < 3.5) {
      float x = (seedPos.x / 4.0) * 15.0;
      float ribbonLane = floor(aLayerId);
      float y = sin(x * 0.28 + t * 0.8 + ribbonLane * 1.2) * 2.2 + (ribbonLane - 1.5) * 1.1 + curl.y * 0.3;
      float z = cos(x * 0.2 + t * 0.5) * 1.5 + curl.z * 0.3;
      return vec3(x, y, z);
    }

    // 4: SIMULATION — Kinetic Event Energy & Pulse Clusters
    if (motifId < 4.5) {
      float pulse = sin(t * 3.0 + aPhase * 4.0) * 0.6;
      vec3 kineticCurl = curlNoise(vec3(seedPos.xy * 0.5, t * 1.2));
      return vec3(seedPos.xy * (1.1 + pulse * 0.2) + kineticCurl.xy * 0.8, seedPos.z + kineticCurl.z * 0.6);
    }

    // 5: SCRIPT — Quiet Peripheral Field (Margins only, center cleared for reading)
    if (motifId < 5.5) {
      // Repel from center box: width [-7.0, 7.0], height [-4.5, 4.5]
      vec2 p = seedPos.xy * 1.35;
      float edgeX = sign(p.x) * (max(abs(p.x), 7.2) + 0.5);
      float edgeY = p.y * 1.2;
      return vec3(mix(p.x, edgeX, 0.82), edgeY + curl.y * 0.12, seedPos.z * 0.4 + curl.z * 0.15);
    }

    // 6: STORYBOARD — Rectangular Cinematic Compositional Frames
    if (motifId < 6.5) {
      // Snap toward 16:9 rectangular boundary with golden ratio rule-of-thirds accents
      float aspect = 16.0 / 9.0;
      vec2 frameBox = vec2(dir.x * 5.6 * aspect, dir.y * 5.6);
      vec2 p = mix(seedPos.xy, frameBox, 0.45) + curl.xy * 0.25;
      return vec3(p, seedPos.z * 0.5 + curl.z * 0.2);
    }

    // 7: EXPORT — Minimal Settled Equilibrium Field
    // Subtle, sparse, calm field
    return vec3(seedPos.xy * 1.25 + curl.xy * 0.15, seedPos.z * 0.3 + sin(t * 0.4 + aPhase) * 0.1);
  }

  void main() {
    vColor = aColor;
    vLayerId = aLayerId;

    // Moody cinematic emergence time multiplier
    float t = uTime * 0.2;

    // 3D Curl Noise vector displacement
    vec3 noiseCoord = vec3(position.xy * 0.32, position.z * 0.5 + t * 0.6);
    vec3 curl = curlNoise(noiseCoord) * uTurbulence;

    // Compute positions for current and next motifs
    vec3 posFrom = computeMotifPosition(uMotifFrom, position, t, curl);
    vec3 posTo   = computeMotifPosition(uMotifTo, position, t, curl);

    // Smooth GPU Interpolation across motifs
    // Cinematic easing curve
    float progress = smoothstep(0.0, 1.0, uMotifProgress);
    vec3 morphedPos = mix(posFrom, posTo, progress);

    // Dynamic Central Column Clearing for SCRIPT view reading focus
    if (uCenterClear > 0.001) {
      float distFromCenter = length(morphedPos.xy);
      vec2 pushDir = distFromCenter > 0.001 ? normalize(morphedPos.xy) : vec2(1.0, 0.0);
      float clearFactor = smoothstep(6.0, 1.0, distFromCenter) * uCenterClear;
      morphedPos.xy += pushDir * clearFactor * 3.5;
    }

    // Dynamic Narrative Energy Flashes:
    // Gold accents flare under turbulence or active accent strength
    float turbulenceMag = length(curl);
    float isGold = (aColor.r > 0.75 && aColor.g > 0.55 && aColor.b < 0.45) ? 1.0 : 0.0;
    vAccent = clamp(isGold + smoothstep(0.4, 0.9, turbulenceMag) * uAccentStrength, 0.0, 1.0);

    // Perspective projection
    vec4 mvPosition = modelViewMatrix * vec4(morphedPos, 1.0);
    gl_Position = projectionMatrix * mvPosition;

    // Perspective point-size attenuation
    float distToCam = max(-mvPosition.z, 0.1);
    vDepth = distToCam;

    float sizeFactor = (aSize * uPointSize * uPointScale) * (380.0 / distToCam);
    gl_PointSize = clamp(sizeFactor, 1.0, 26.0);

    // Entrance resolve opacity
    vAlpha = smoothstep(0.0, 0.6, uProgress);
  }
`;

export const granularFragmentShader = /* glsl */ `
  precision mediump float;

  uniform float uOpacity;
  uniform float uDepthFade;
  uniform float uAmberBoost;

  varying vec3 vColor;
  varying float vAlpha;
  varying float vDepth;
  varying float vLayerId;
  varying float vAccent;

  void main() {
    // Circular particle sprite with Gaussian falloff (soft glowing edges)
    vec2 coord = gl_PointCoord - vec2(0.5);
    float distSq = dot(coord, coord);
    if (distSq > 0.25) {
      discard;
    }

    float dist = sqrt(distSq);

    // Soft Gaussian circular falloff
    float gaussian = exp(-distSq * 18.0) * smoothstep(0.5, 0.06, dist);

    // Design Tokens:
    // --text-primary (#F5F3EF): vec3(0.961, 0.953, 0.937)
    // --accent (#C9A46B): vec3(0.788, 0.643, 0.420)
    // Luminous gold: vec3(0.88, 0.72, 0.36)
    vec3 colPrimary = vec3(0.961, 0.953, 0.937);
    vec3 colAccent = vec3(0.85, 0.68, 0.38);

    // Occasional subtle flashes of amber gold represent narrative energy
    float accentMix = clamp(vAccent + uAmberBoost * 0.35, 0.0, 1.0);
    vec3 finalColor = mix(vColor, colAccent, accentMix);

    // Luminous nucleus core in the center of the particle
    finalColor += colAccent * (accentMix * 0.4 * exp(-distSq * 32.0));

    // Atmospheric depth attenuation
    float depthAtten = clamp(1.0 - (vDepth - 6.0) * (uDepthFade * 0.03), 0.25, 1.0);

    float finalAlpha = gaussian * vAlpha * uOpacity * depthAtten;
    gl_FragColor = vec4(finalColor, finalAlpha);
  }
`;
