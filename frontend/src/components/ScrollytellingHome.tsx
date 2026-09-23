import React, { useState, useEffect, useRef } from 'react';
import { ProjectMetadata } from '../types';
import {
  ParticleDivider,
} from './granular';
import { Footer } from './layout/Footer';

interface ScrollytellingHomeProps {
  onStartNew: () => void;
  onOpenProject: (projectId: string) => void;
  projects: ProjectMetadata[];
}

export const ScrollytellingHome: React.FC<ScrollytellingHomeProps> = ({
  onStartNew,
  onOpenProject,
  projects,
}) => {
  const [scrollProgress, setScrollProgress] = useState(0);
  const [activeCard, setActiveCard] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleScroll = () => {
      if (!containerRef.current) return;
      const el = containerRef.current;
      const totalHeight = el.scrollHeight - window.innerHeight;
      if (totalHeight > 0) {
        const progress = Math.min(1, Math.max(0, el.scrollTop / totalHeight));
        setScrollProgress(progress);
      }
    };

    const el = containerRef.current;
    if (el) {
      el.addEventListener('scroll', handleScroll, { passive: true });
    }
    return () => {
      if (el) {
        el.removeEventListener('scroll', handleScroll);
      }
    };
  }, []);

  // Compute text opacities/scales based on scrollProgress
  const writtenOpacity = Math.max(0, 1 - scrollProgress * 3.5);
  const writtenScale = 1 - scrollProgress * 0.05;

  const emergesOpacity = Math.min(1, 0.4 + scrollProgress * 2.5);
  const emergesScale = 1 + scrollProgress * 0.05;

  // Filter projects by search query
  const filteredProjects = projects.filter((p) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      p.title.toLowerCase().includes(q) ||
      p.seed_prompt.toLowerCase().includes(q) ||
      (p.input_type && p.input_type.toLowerCase().includes(q))
    );
  });

  const renderProductionRail = (p: ProjectMetadata) => {
    const hasEvents = p.total_events > 0 || p.current_tick > 0;
    const hasScenes = p.total_scenes > 0;
    const hasPanels = (p.total_panels || 0) > 0;
    const isExportReady = hasPanels;

    return (
      <div className="portfolio-pipeline-rail" aria-label="Production milestone rail">
        <span className="rail-step complete">
          <span className="rail-indicator">●</span>
          <span className="rail-label">WORLD</span>
        </span>
        <span className="rail-divider" />
        <span className={`rail-step ${hasEvents ? 'complete' : 'pending'}`}>
          <span className="rail-indicator">{hasEvents ? '●' : '○'}</span>
          <span className="rail-label">SIM</span>
        </span>
        <span className="rail-divider" />
        <span className={`rail-step ${hasScenes ? 'complete' : 'pending'}`}>
          <span className="rail-indicator">{hasScenes ? '●' : '○'}</span>
          <span className="rail-label">SCRIPT</span>
        </span>
        <span className="rail-divider" />
        <span className={`rail-step ${hasPanels ? 'complete' : 'pending'}`}>
          <span className="rail-indicator">{hasPanels ? '●' : '○'}</span>
          <span className="rail-label">BOARD</span>
        </span>
        <span className="rail-divider" />
        <span className={`rail-step ${isExportReady ? 'complete' : 'pending'}`}>
          <span className="rail-indicator">{isExportReady ? '●' : '○'}</span>
          <span className="rail-label">EXPORT</span>
        </span>
      </div>
    );
  };

  return (
    <div className="scrolly-container" ref={containerRef}>
      {/* SECTION 01: HERO */}
      <section className="scrolly-section hero-section" aria-label="Hero Section">
        <div className="hero-central-composition">
          <div className="hero-eyebrow">
            <span className="eyebrow-glyph" aria-hidden="true">❖</span>
            <span className="hero-kicker">AGENTIC PROCEDURAL NARRATIVE ENGINE</span>
          </div>

          <h1 className="hero-editorial-title">D3 STORY LAB</h1>

          <div className="hero-statement-container">
            <div
              className="statement-line statement-receding"
              style={{
                opacity: writtenOpacity,
                transform: `scale(${writtenScale}) translateZ(0)`,
              }}
            >
              THE STORY IS NOT WRITTEN.
            </div>
            <div
              className="statement-line statement-emerging"
              style={{
                opacity: emergesOpacity,
                transform: `scale(${emergesScale}) translateZ(0)`,
              }}
            >
              IT EMERGES.
            </div>
          </div>

          <p className="hero-prose">
            Autonomous characters make decisions inside a deterministic world.
            Narrative arcs, subtext, causality, screenplay, and storyboard emerge from simulation.
          </p>

          <div className="hero-actions">
            <button
              type="button"
              className="btn-pill-primary btn-cinematic-primary"
              onClick={onStartNew}
            >
              <span>NEW SIMULATION</span>
              <span className="btn-arrow" aria-hidden="true">→</span>
            </button>
            {projects.length > 0 && (
              <button
                type="button"
                className="btn-pill-secondary btn-cinematic-secondary"
                onClick={() => onOpenProject(projects[0].id)}
              >
                <span>OPEN PROJECT ({projects[0].title})</span>
              </button>
            )}
          </div>


          {/* Minimal Project / Engine Metadata Strip */}
          <div className="hero-metadata-strip" aria-label="System status strip">
            <div className="metadata-strip-item">
              <span className="strip-label">ENGINE</span>
              <strong className="strip-val">DETERMINISTIC HYBRID</strong>
            </div>
            <span className="strip-sep" aria-hidden="true">/</span>
            <div className="metadata-strip-item">
              <span className="strip-label">EXECUTION</span>
              <strong className="strip-val">LOCAL ZERO-AI FALLBACK</strong>
            </div>
            <span className="strip-sep" aria-hidden="true">/</span>
            <div className="metadata-strip-item">
              <span className="strip-label">FIREWALL</span>
              <strong className="strip-val">SCENE PROJECTION ONLY</strong>
            </div>
            {projects.length > 0 && (
              <>
                <span className="strip-sep" aria-hidden="true">/</span>
                <div className="metadata-strip-item">
                  <span className="strip-label">ACTIVE DOSSIER</span>
                  <strong className="strip-val text-amber">
                    {projects[0].title.toUpperCase()} (T{projects[0].current_tick})
                  </strong>
                </div>
              </>
            )}
          </div>
        </div>

        <div className="scroll-indicator" aria-hidden="true">
          <span>SCROLL TO EXPLORE ARCHITECTURE</span>
          <div className="scroll-notch" />
        </div>
      </section>

      <ParticleDivider seed={501} width="85%" />

      {/* SECTION 02: THE SPARK */}
      <section className="scrolly-section split-editorial-section">
        <div className="split-left">
          <div className="section-index">02 / SPARK</div>
          <h2 className="split-large-title">
            DROP IN<br />AN IDEA.
          </h2>
          <p className="split-subtext">
            Prompt. Clipping. Incident. Scenario. Choose beginning, midpoint, ending, or full concept.
          </p>
          <div style={{ marginTop: '24px' }}>
            <button className="btn-pill-primary btn-cinematic-primary" onClick={onStartNew}>
              CONFIGURE SIMULATION
            </button>
          </div>
        </div>

        <div className="split-right">
          <div className="spark-input-simulation">
            <div className="spark-prompt-box">
              <div className="spark-label">NARRATIVE INPUT</div>
              <div className="spark-text">
                "In a rain-slicked luxury penthouse, investigative journalist Maya Lin confronts diplomat Arjun Mehta regarding a confidential offshore ledger before unknown forces intervene."
              </div>
            </div>

            <div className="spark-breakdown-arrow">↓ STRUCTURAL EXTRACTION</div>

            <div className="spark-concepts-grid">
              <div className="concept-chip">
                <span className="chip-label">CHARACTERS</span>
                <strong>Maya Lin, Arjun Mehta</strong>
              </div>
              <div className="concept-chip">
                <span className="chip-label">PLACE</span>
                <strong>Penthouse Suite, Service Hall</strong>
              </div>
              <div className="concept-chip">
                <span className="chip-label">CONFLICT</span>
                <strong>Bribery Exposure vs Cover-up</strong>
              </div>
              <div className="concept-chip">
                <span className="chip-label">OBJECTS</span>
                <strong>Classified Ledger, Audio Bug</strong>
              </div>
              <div className="concept-chip">
                <span className="chip-label">SECRETS</span>
                <strong>Forged credentials, Hidden warrant</strong>
              </div>
            </div>
          </div>
        </div>
      </section>

      <ParticleDivider seed={502} width="85%" />

      {/* SECTION 03: CAST */}

      <section className="scrolly-section split-editorial-section cast-section">
        <div className="split-left sticky-title-col">
          <div className="section-index">03 / CHARACTERS</div>
          <h2 className="split-large-title">CAST</h2>
          <p className="split-subtext">
            Autonomous digital actors with private knowledge boundaries.
          </p>
        </div>

        <div className="split-right">
          <div className="cast-stack">
            {[
              {
                name: 'MAYA LIN',
                role: 'Investigative Journalist',
                goal: 'Expose offshore account beneficiaries',
                state: 'Hyper-vigilant',
                trust: 'Arjun: 32%',
                belief: 'Arjun is stalling for security backup',
                secret: 'Possesses an unauthorized wiretap warrant',
              },
              {
                name: 'ARJUN MEHTA',
                role: 'Diplomatic Envoy',
                goal: 'Destroy physical audit trail',
                state: 'Pressured',
                trust: 'Maya: 18%',
                belief: 'Maya does not yet have document proof',
                secret: 'The courier envelope in the safe is empty',
              },
            ].map((actor, idx) => (
              <div
                key={actor.name}
                className={`scrolly-actor-card ${activeCard === idx ? 'card-active' : 'card-receding'}`}
                onMouseEnter={() => setActiveCard(idx)}
              >
                <div className="card-topline">
                  <div>
                    <h3 className="actor-title">{actor.name}</h3>
                    <div className="actor-subtitle">{actor.role}</div>
                  </div>
                  <span className="actor-state-badge">{actor.state}</span>
                </div>

                <div className="actor-field">
                  <span className="field-tag">GOAL</span>
                  <div className="field-val">{actor.goal}</div>
                </div>

                <div className="actor-field">
                  <span className="field-tag">TRUST</span>
                  <div className="field-val">{actor.trust}</div>
                </div>

                <div className="actor-private-divider">
                  <span>PRIVATE BOUNDARY</span>
                </div>

                <div className="actor-field">
                  <span className="field-tag">BELIEF</span>
                  <div className="field-val text-muted">{actor.belief}</div>
                </div>

                <div className="actor-field">
                  <span className="field-tag">SECRET</span>
                  <div className="field-val text-amber">{actor.secret}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <ParticleDivider seed={503} width="85%" />

      {/* SECTION 04: SANDBOX */}
      <section className="scrolly-section split-editorial-section">
        <div className="split-left">
          <div className="section-index">04 / SANDBOX</div>
          <h2 className="split-large-title">
            LET THEM<br />LOOSE.
          </h2>
          <p className="split-subtext">
            Perception. Deliberation. Emergence.
          </p>
        </div>

        <div className="split-right">
          <div className="sandbox-timeline-stream">
            {[
              { tick: '00:01', desc: 'Maya enters the room.', tag: 'MOVE' },
              { tick: '00:02', desc: 'Arjun hides the file.', tag: 'OBJECT' },
              { tick: '00:03', desc: 'Maya notices the open drawer.', tag: 'PERCEPTION' },
              { tick: '00:04', desc: 'Trust drops.', tag: 'STATE' },
              { tick: '00:05', desc: 'Maya confronts Arjun: "Where is the ledger?"', tag: 'SPEAK' },
            ].map((evt) => (
              <div key={evt.tick} className="timeline-entry">
                <span className="entry-tick">{evt.tick}</span>
                <span className="entry-tag">{evt.tag}</span>
                <span className="entry-desc">{evt.desc}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <ParticleDivider seed={504} width="85%" />

      {/* SECTION 05: DIRECTOR */}
      <section className="scrolly-section split-editorial-section">
        <div className="split-left">
          <div className="section-index">05 / DIRECTOR</div>
          <h2 className="split-large-title">
            PRESSURE.<br />NOT PUPPETRY.
          </h2>
          <p className="split-subtext">
            The Director does not write dialogue. It changes the world.
          </p>
        </div>

        <div className="split-right">
          <div className="director-interventions-stack">
            {[
              { title: 'LIGHTS FAIL', desc: 'Power cuts across the floor. Visibility drops.' },
              { title: 'PHONE RINGS', desc: 'An unlisted secure landline begins ringing.' },
              { title: 'DOOR LOCKS', desc: 'Electronic deadbolts seal the perimeter exit.' },
              { title: 'NEW EVIDENCE', desc: 'A courier envelope slides under the door.' },
              { title: 'SOMEONE ARRIVES', desc: 'Footsteps approach rapidly in the outer hallway.' },
            ].map((d) => (
              <div key={d.title} className="director-intervention-card">
                <div className="director-card-header">
                  <span className="director-badge">DIRECTOR</span>
                  <span className="director-title">{d.title}</span>
                </div>
                <div className="director-desc">{d.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <ParticleDivider seed={505} width="85%" />

      {/* SECTION 06: SCRIBE */}
      <section className="scrolly-section split-editorial-section">
        <div className="split-left">
          <div className="section-index">06 / SCRIBE</div>
          <h2 className="split-large-title">
            WATCH.<br />TRANSCRIBE.
          </h2>
          <p className="split-subtext">
            Verified events convert directly into Fountain screenplay format. Scribe observes; it never invents.
          </p>
        </div>

        <div className="split-right">
          <div className="scribe-comparison-grid">
            <div className="scribe-raw-column">
              <div className="column-label">RAW SIMULATION EVENTS</div>
              <div className="raw-event-item">00:01 Maya enters Penthouse.</div>
              <div className="raw-event-item">00:02 Arjun catches sight of her.</div>
              <div className="raw-event-item">00:03 Arjun conceals dossier under desk.</div>
              <div className="raw-event-item">00:04 Maya: "Where is the ledger?"</div>
            </div>

            <div className="scribe-fountain-column">
              <div className="column-label">FOUNTAIN SCREENPLAY OUTPUT</div>
              <div className="fountain-paper-snippet">
                <div className="fountain-slugline">INT. PENTHOUSE SUITE - NIGHT</div>
                <div className="fountain-action">Maya enters, rain drumming against the panoramic glass.</div>
                <div className="fountain-action">Arjun catches sight of her, quickly sliding the leather dossier beneath the desk.</div>
                <div className="fountain-char">MAYA</div>
                <div className="fountain-dialogue">Where is the ledger?</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <ParticleDivider seed={506} width="85%" />

      {/* SECTION 07: STORYBOARD */}
      <section className="scrolly-section split-editorial-section">
        <div className="split-left">
          <div className="section-index">07 / STORYBOARD</div>
          <h2 className="split-large-title">
            FROM EVENT<br />TO FRAME.
          </h2>
          <p className="split-subtext">
            Screenplay beats translated into structured cinematic framing shot plans.
          </p>
        </div>

        <div className="split-right">
          <div className="storyboard-filmstrip">
            {[
              { shot: 'SHOT 01', type: 'WIDE', angle: 'EYE LEVEL', desc: 'Penthouse interior with skyline silhouette.' },
              { shot: 'SHOT 02', type: 'MEDIUM', angle: 'LOW ANGLE', desc: 'Maya halts at the threshold, drenched.' },
              { shot: 'SHOT 03', type: 'CLOSE UP', angle: 'HIGH ANGLE', desc: 'Arjun’s fingers slipping the dossier under mahogany desk.' },
              { shot: 'SHOT 04', type: 'OVER SHOULDER', angle: 'DUTCH ANGLE', desc: 'Two actors locked in silent visual confrontation.' },
            ].map((p) => (
              <div key={p.shot} className="storyboard-panel-mock">
                <div className="panel-aspect-frame">
                  <div className="panel-inner-wireframe">
                    <span className="wireframe-crosshair" />
                    <span className="panel-shot-id">{p.shot}</span>
                  </div>
                </div>
                <div className="panel-meta">
                  <span className="panel-tag">{p.type}</span>
                  <span className="panel-tag">{p.angle}</span>
                </div>
                <div className="panel-caption">{p.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <ParticleDivider seed={507} width="85%" />

      {/* SECTION 08: PRODUCTION PORTFOLIO */}
      <section className="scrolly-section portfolio-section">
        <div className="portfolio-header-block">
          <div className="section-index">08 / PRODUCTIONS</div>
          <h2 className="split-large-title">
            ACTIVE<br />PRODUCTIONS.
          </h2>
          <p className="split-subtext" style={{ maxWidth: '640px', margin: '0 auto 24px auto', textAlign: 'center' }}>
            Autonomous emergent narrative sandboxes in active development.
          </p>

          <div className="portfolio-search-bar">
            <input
              type="text"
              className="portfolio-search-input"
              placeholder="Filter productions by title, premise, or prompt..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Filter active productions"
            />
            {searchQuery && (
              <button
                type="button"
                className="portfolio-search-clear"
                onClick={() => setSearchQuery('')}
                aria-label="Clear filter"
              >
                ✕
              </button>
            )}
          </div>
        </div>

        {filteredProjects.length === 0 ? (
          <div className="portfolio-empty-box">
            {projects.length === 0 ? (
              <>
                <p style={{ color: '#94a3b8', fontSize: '13px', marginBottom: '16px' }}>
                  No narrative simulations created yet.
                </p>
                <button className="btn-pill-primary btn-cinematic-primary" onClick={onStartNew}>
                  + INITIALIZE FIRST SIMULATION
                </button>
              </>
            ) : (
              <>
                <p style={{ color: '#94a3b8', fontSize: '13px', marginBottom: '16px' }}>
                  No simulations match "{searchQuery}".
                </p>
                <button className="btn-pill-secondary btn-cinematic-secondary" onClick={() => setSearchQuery('')}>
                  Clear Filter
                </button>
              </>
            )}
          </div>
        ) : (
          <div className="portfolio-cards-grid">
            {filteredProjects.map((p) => (
              <div
                key={p.id}
                className="portfolio-project-card"
                onClick={() => onOpenProject(p.id)}
                title={`Open ${p.title} workstation`}
              >
                <div className="portfolio-card-header">
                  <div>
                    <span className="portfolio-card-kicker">
                      {p.input_type ? p.input_type.toUpperCase().replace('_', ' ') : 'NARRATIVE SANDBOX'}
                    </span>
                    <h3 className="portfolio-card-title">{p.title}</h3>
                  </div>
                  <span className="portfolio-card-duration">
                    ⏱ {p.target_duration_minutes || 20}m
                  </span>
                </div>

                <p className="portfolio-card-prompt">
                  "{p.seed_prompt}"
                </p>

                {renderProductionRail(p)}

                <div className="portfolio-card-footer">
                  <div className="portfolio-stats-group">
                    <span className="portfolio-stat-pill">TICK {p.current_tick}</span>
                    <span className="portfolio-stat-pill">{p.total_events} EVENTS</span>
                    <span className="portfolio-stat-pill">{p.total_scenes} SCENES</span>
                  </div>
                  <span className="portfolio-open-link">
                    WORKSTATION →
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* BOTTOM CTA */}
      <section className="scrolly-section cta-final-section">
        <h2 className="cta-statement">THE STORY IS NOT WRITTEN. IT EMERGES.</h2>
        <div className="hero-actions">
          <button className="btn-pill-primary btn-cinematic-primary" onClick={onStartNew}>
            BUILD WORLD
          </button>
          {projects.length > 0 && (
            <button
              className="btn-pill-secondary btn-cinematic-secondary"
              onClick={() => onOpenProject(projects[0].id)}
            >
              ENTER WORKSTATION
            </button>
          )}
        </div>
      </section>

      {/* Editorial Architectural Index Footer */}
      <Footer />
    </div>
  );
};
