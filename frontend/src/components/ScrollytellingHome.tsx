import React, { useState, useEffect, useRef } from 'react';
import { ProjectMetadata } from '../types';

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
      if (el) el.removeEventListener('scroll', handleScroll);
    };
  }, []);

  // Section 01: Hero statement morph calculation
  // As user starts scrolling (0.0 to 0.15), 'WRITTEN' recedes, 'EMERGES' comes forward
  const writtenOpacity = Math.max(0.15, 1 - scrollProgress * 7);
  const writtenScale = Math.max(0.85, 1 - scrollProgress * 1.2);
  const emergesOpacity = Math.min(1, 0.4 + scrollProgress * 5);
  const emergesScale = Math.min(1.15, 1 + scrollProgress * 0.8);

  return (
    <div className="scrolly-container" ref={containerRef}>
      {/* SECTION 01: HERO */}
      <section className="scrolly-section hero-section">
        <div className="hero-kicker">AGENTIC PROCEDURAL NARRATIVE ENGINE</div>
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
          Autonomous characters. Conflicting goals. Living narratives.
        </p>

        <div className="hero-actions">
          <button className="btn-cinematic-primary" onClick={onStartNew}>
            NEW SIMULATION
          </button>
          {projects.length > 0 && (
            <button
              className="btn-cinematic-secondary"
              onClick={() => onOpenProject(projects[0].id)}
            >
              OPEN PROJECT ({projects[0].title})
            </button>
          )}
        </div>

        {/* Short Pipeline Summary */}
        <div className="pipeline-flow-minimal">
          <span>IDEA</span>
          <span className="flow-arrow">↓</span>
          <span>ACTORS</span>
          <span className="flow-arrow">↓</span>
          <span>SANDBOX</span>
          <span className="flow-arrow">↓</span>
          <span>EVENTS</span>
          <span className="flow-arrow">↓</span>
          <span>SCREENPLAY</span>
        </div>

        <div className="scroll-indicator">
          <span>SCROLL TO EXPLORE</span>
          <div className="scroll-notch" />
        </div>
      </section>

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
            <button className="btn-cinematic-primary" onClick={onStartNew}>
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

      {/* BOTTOM CTA */}
      <section className="scrolly-section cta-final-section">
        <h2 className="cta-statement">THE STORY IS NOT WRITTEN. IT EMERGES.</h2>
        <div className="hero-actions">
          <button className="btn-cinematic-primary" onClick={onStartNew}>
            BUILD WORLD
          </button>
          {projects.length > 0 && (
            <button
              className="btn-cinematic-secondary"
              onClick={() => onOpenProject(projects[0].id)}
            >
              ENTER WORKSTATION
            </button>
          )}
        </div>
      </section>
    </div>
  );
};
