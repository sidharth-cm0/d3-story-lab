/**
 * Footer.tsx
 *
 * Minimalist Multi-Column Editorial Technical Footer for D3 Story Lab:
 * - Four forensic architectural pillars: SYSTEM, NARRATIVE, TOOLS, ENGINE
 * - Restrained typography in IBM Plex Mono & Archivo
 * - Provenance metadata and deterministic invariant certification
 * - Generous breathing room and high-contrast accessibility
 */

import React from 'react';

export const Footer: React.FC = () => {
  return (
    <footer className="app-editorial-footer" role="contentinfo" aria-label="D3 Story Lab Architectural Index">
      <div className="footer-top-divider" aria-hidden="true" />

      <div className="footer-content-grid">
        {/* Pillar 1: SYSTEM */}
        <div className="footer-column">
          <span className="footer-column-kicker">01 / SYSTEM</span>
          <h4 className="footer-column-title">SIMULATION ENGINE</h4>
          <ul className="footer-links-list">
            <li><span className="footer-item">World State Topology</span></li>
            <li><span className="footer-item">Autonomous Decision Loop</span></li>
            <li><span className="footer-item">Story Structure Engine</span></li>
            <li><span className="footer-item">Forensic Observer</span></li>
            <li><span className="footer-item">Observable Scene Builder</span></li>
          </ul>
        </div>

        {/* Pillar 2: NARRATIVE */}
        <div className="footer-column">
          <span className="footer-column-kicker">02 / NARRATIVE</span>
          <h4 className="footer-column-title">EMERGENT DRAMATURGY</h4>
          <ul className="footer-links-list">
            <li><span className="footer-item">Character Arcs & Trajectories</span></li>
            <li><span className="footer-item">Subtext & Objective Preservation</span></li>
            <li><span className="footer-item">Screenplay Transcription</span></li>
            <li><span className="footer-item">Storyboard Shot Planner</span></li>
            <li><span className="footer-item">Visual Bible & Grounding</span></li>
          </ul>
        </div>

        {/* Pillar 3: TOOLS */}
        <div className="footer-column">
          <span className="footer-column-kicker">03 / TOOLS</span>
          <h4 className="footer-column-title">VERIFICATION & EXPORT</h4>
          <ul className="footer-links-list">
            <li><span className="footer-item">Bidirectional Provenance</span></li>
            <li><span className="footer-item">Fountain Screenplay Export</span></li>
            <li><span className="footer-item">Storyboard PDF Production</span></li>
            <li><span className="footer-item">Quality Rubrics & Gates</span></li>
            <li><span className="footer-item">Project State Dossiers</span></li>
          </ul>
        </div>

        {/* Pillar 4: ENGINE */}
        <div className="footer-column">
          <span className="footer-column-kicker">04 / ENGINE</span>
          <h4 className="footer-column-title">ARCHITECTURAL INVARIANTS</h4>
          <ul className="footer-links-list">
            <li><span className="footer-item text-amber">Deterministic Rule Decision Policy</span></li>
            <li><span className="footer-item">Immutable Event History</span></li>
            <li><span className="footer-item">Causal Chain Traceability</span></li>
            <li><span className="footer-item">Omniscience Firewall Gate</span></li>
            <li><span className="footer-item">Narrative Sufficiency Check</span></li>
          </ul>
        </div>
      </div>

      <div className="footer-bottom-bar">
        <div className="footer-brand-lockup">
          <span className="footer-glyph" aria-hidden="true">❖</span>
          <span className="footer-brand-name">D3 ARCHITECTURAL INDEX</span>
          <span className="footer-bar-sep" aria-hidden="true">/</span>
          <span className="footer-tagline">AGENTIC PROCEDURAL NARRATIVE SIMULATION</span>
        </div>

        <div className="footer-provenance-badge">
          <span className="provenance-dot" aria-hidden="true" />
          <span className="provenance-text">CANONICAL DETERMINISTIC PROVENANCE VERIFIED</span>
        </div>
      </div>
    </footer>
  );
};
