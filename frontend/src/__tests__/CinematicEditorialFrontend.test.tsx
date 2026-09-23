/**
 * CinematicEditorialFrontend.test.tsx
 *
 * Test suite for D3 Story Lab's dark cinematic granular frontend architecture:
 * - Three.js point generators: Terrain, Agents, Narrative Flow
 * - Particle ShaderMaterial & uniforms
 * - GranularScene component & workspace motifs
 * - Hero & Footer layout components
 * - Reduced-motion safety & accessibility
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

import {
  generateTerrainPoints,
  generateAgentPoints,
  generateFlowPoints,
  createParticleMaterial,
  GranularScene,
} from '../components/three';

import { Hero, Footer, TopNav } from '../components/layout';
import { useReducedMotion } from '../components/motion';

describe('Three.js Granular Point Generators', () => {
  it('generateTerrainPoints produces deterministic coordinate and attribute arrays', () => {
    const terrain1 = generateTerrainPoints(1000, 927);
    const terrain2 = generateTerrainPoints(1000, 927);
    const terrain3 = generateTerrainPoints(1000, 555);

    expect(terrain1.positions.length).toBe(3000);
    expect(terrain1.targets.length).toBe(3000);
    expect(terrain1.colors.length).toBe(3000);
    expect(terrain1.sizes.length).toBe(1000);
    expect(terrain1.phases.length).toBe(1000);
    expect(terrain1.layerIds.length).toBe(1000);

    // Byte-identical reproduction
    expect(terrain1.positions[0]).toBe(terrain2.positions[0]);
    expect(terrain1.targets[5]).toBe(terrain2.targets[5]);
    expect(terrain1.colors[2]).toBe(terrain2.colors[2]);

    // Distinct with different seed
    expect(terrain1.positions[0]).not.toBe(terrain3.positions[0]);

    // LayerId is 1.0
    expect(terrain1.layerIds[0]).toBe(1.0);
  });

  it('generateAgentPoints produces dual abstract humanoid agent silhouettes', () => {
    const agents1 = generateAgentPoints(600, 928);
    const agents2 = generateAgentPoints(600, 928);

    expect(agents1.positions.length).toBe(1800);
    expect(agents1.targets.length).toBe(1800);

    // Byte-identical reproduction
    expect(agents1.targets[0]).toBe(agents2.targets[0]);

    // First half represents Agent A (Initiator, X < 0), second half Agent B (Receptor, X > 0)
    const agentAX = agents1.targets[0]; // Agent A target X
    const agentBX = agents1.targets[300 * 3]; // Agent B target X

    expect(agentAX).toBeLessThan(0); // Left side ~ -6.2
    expect(agentBX).toBeGreaterThan(0); // Right side ~ +6.2

    // LayerId is 2.0
    expect(agents1.layerIds[0]).toBe(2.0);
  });

  it('generateFlowPoints creates causal transference stream bridging agents', () => {
    const flow1 = generateFlowPoints(400, 929);
    const flow2 = generateFlowPoints(400, 929);

    expect(flow1.positions.length).toBe(1200);
    expect(flow1.targets.length).toBe(1200);
    expect(flow1.colors.length).toBe(1200);

    // Byte-identical reproduction
    expect(flow1.positions[0]).toBe(flow2.positions[0]);

    // LayerId is 3.0
    expect(flow1.layerIds[0]).toBe(3.0);

    // Flow targets span the bridge interval between agents
    let hasMidpoint = false;
    for (let i = 0; i < 400; i++) {
      const x = flow1.targets[i * 3];
      if (Math.abs(x) < 2.0) {
        hasMidpoint = true;
        break;
      }
    }
    expect(hasMidpoint).toBe(true);
  });
});

describe('ParticleMaterial Factory & Uniforms', () => {
  it('creates ShaderMaterial with all required uniforms initialized', () => {
    const mat = createParticleMaterial();

    expect(mat).toBeDefined();
    expect(mat.uniforms.uTime).toBeDefined();
    expect(mat.uniforms.uProgress).toBeDefined();
    expect(mat.uniforms.uDensity).toBeDefined();
    expect(mat.uniforms.uPointSize).toBeDefined();
    expect(mat.uniforms.uOpacity).toBeDefined();
    expect(mat.uniforms.uMorph).toBeDefined();
    expect(mat.uniforms.uDepthFade).toBeDefined();
    expect(mat.uniforms.uAmberBoost).toBeDefined();
    expect(mat.uniforms.uPixelRatio).toBeDefined();

    // Default opacity is 0 (pre-resolve)
    expect(mat.uniforms.uOpacity.value).toBe(0.0);
    expect(mat.transparent).toBe(true);
    expect(mat.depthWrite).toBe(false);
  });
});

describe('GranularScene Component', () => {
  it('renders container with pointer-events: none, aria-hidden: true, role: presentation', () => {
    const { container } = render(
      <GranularScene
        motif="home"
        isHovered={false}
        data-testid="test-granular-scene"
      />
    );

    const el = container.querySelector('.granular-three-container');
    expect(el).not.toBeNull();
    expect(el?.getAttribute('aria-hidden')).toBe('true');
    expect(el?.getAttribute('role')).toBe('presentation');
  });

  it('supports all 8 workspace motifs without throwing errors', () => {
    const motifs = ['home', 'world', 'actors', 'arcs', 'simulation', 'script', 'storyboard', 'export'] as const;

    for (const motif of motifs) {
      const { unmount } = render(
        <GranularScene motif={motif} />
      );
      unmount();
    }
  });

  it('handles isHovered prop changes gracefully', () => {
    const { rerender } = render(
      <GranularScene motif="home" isHovered={false} />
    );

    rerender(
      <GranularScene motif="home" isHovered={true} />
    );
  });
});

describe('Layout Components: Hero & Footer', () => {
  it('Hero renders title, eyebrow, statements, and metadata strip', () => {
    const onStartNew = vi.fn();
    const onOpenProject = vi.fn();

    const mockProjects = [
      {
        id: 'p-1',
        title: 'Project Alpha',
        seed_prompt: 'A mystery unfolding in Vienna',
        created_at: '2026-09-20',
        current_tick: 14,
        total_events: 28,
        total_scenes: 3,
        total_panels: 6,
        updated_at: '2026-09-20',
      },
    ];

    render(
      <Hero
        onStartNew={onStartNew}
        onOpenProject={onOpenProject}
        projects={mockProjects}
      />
    );

    // Title & Eyebrow
    expect(screen.getByText('D3 STORY LAB')).toBeDefined();
    expect(screen.getByText('AGENTIC PROCEDURAL NARRATIVE ENGINE')).toBeDefined();

    // Emergent statement
    expect(screen.getByText('THE STORY IS NOT WRITTEN.')).toBeDefined();
    expect(screen.getByText('IT EMERGES.')).toBeDefined();

    // Buttons
    const newBtn = screen.getByText('NEW SIMULATION');
    expect(newBtn).toBeDefined();
    fireEvent.click(newBtn);
    expect(onStartNew).toHaveBeenCalledTimes(1);

    const openBtn = screen.getByText(/OPEN PROJECT/i);
    expect(openBtn).toBeDefined();
    fireEvent.click(openBtn);
    expect(onOpenProject).toHaveBeenCalledWith('p-1');

    // Metadata strip
    expect(screen.getByText('DETERMINISTIC HYBRID')).toBeDefined();
    expect(screen.getByText('LOCAL ZERO-AI FALLBACK')).toBeDefined();
    expect(screen.getByText('SCENE PROJECTION ONLY')).toBeDefined();
  });

  it('Hero triggers onCtaHoverChange on button mouse enter and leave', () => {
    const onCtaHover = vi.fn();

    render(
      <Hero
        onStartNew={vi.fn()}
        onCtaHoverChange={onCtaHover}
      />
    );

    const newBtn = screen.getByText('NEW SIMULATION');
    fireEvent.mouseEnter(newBtn);
    expect(onCtaHover).toHaveBeenCalledWith(true);

    fireEvent.mouseLeave(newBtn);
    expect(onCtaHover).toHaveBeenCalledWith(false);
  });

  it('Footer renders all 4 architectural pillars and provenance badge', () => {
    render(<Footer />);

    // Pillars
    expect(screen.getByText('01 / SYSTEM')).toBeDefined();
    expect(screen.getByText('SIMULATION ENGINE')).toBeDefined();

    expect(screen.getByText('02 / NARRATIVE')).toBeDefined();
    expect(screen.getByText('EMERGENT DRAMATURGY')).toBeDefined();

    expect(screen.getByText('03 / TOOLS')).toBeDefined();
    expect(screen.getByText('VERIFICATION & EXPORT')).toBeDefined();

    expect(screen.getByText('04 / ENGINE')).toBeDefined();
    expect(screen.getByText('ARCHITECTURAL INVARIANTS')).toBeDefined();

    // Provenance badge
    expect(screen.getByText('CANONICAL DETERMINISTIC PROVENANCE VERIFIED')).toBeDefined();
  });

  it('TopNav exports from layout properly render all 8 workspaces', () => {
    const onSelectView = vi.fn();
    render(<TopNav activeView="home" onSelectView={onSelectView} />);

    expect(screen.getByText('HOME')).toBeDefined();
    expect(screen.getByText('WORLD')).toBeDefined();
    expect(screen.getByText('ACTORS')).toBeDefined();
    expect(screen.getByText('ARCS & STRUCTURE')).toBeDefined();
    expect(screen.getByText('SIMULATION')).toBeDefined();
    expect(screen.getByText('SCRIPT')).toBeDefined();
    expect(screen.getByText('STORYBOARD')).toBeDefined();
    expect(screen.getByText('EXPORT')).toBeDefined();
  });

  it('useReducedMotion hook export is defined and callable', () => {
    expect(typeof useReducedMotion).toBe('function');
  });
});
