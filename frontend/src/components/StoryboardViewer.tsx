import React, { useState, useEffect } from 'react';
import {
  ProjectData,
  StoryboardResponse,
  StoryboardPanel,
  VisualBible,
  ContinuityReport,
} from '../types';
import {
  fetchVisualBible,
  planStoryboard,
  regeneratePanelVersion,
  selectPanelVersion,
  regeneratePage,
  externalRenderPanel,
  externalRenderPage,
} from '../api';
import { formatDisplayValue, safeExtractSvg } from '../utils/format';

interface StoryboardViewerProps {
  project: ProjectData;
  loading?: boolean;
}

type SubTab = 'comic' | 'grid' | 'presentation' | 'bible' | 'continuity';

export const StoryboardViewer: React.FC<StoryboardViewerProps> = ({ project }) => {
  const [storyboardData, setStoryboardData] = useState<StoryboardResponse | null>(null);
  const [visualBible, setVisualBible] = useState<VisualBible | null>(null);
  const [activeTab, setActiveTab] = useState<SubTab>('grid');
  const [activePage, setActivePage] = useState<number>(1);
  const [presentationIndex, setPresentationIndex] = useState<number>(0);
  const [densityMode, setDensityMode] = useState<string>('standard');
  const [selectedPanel, setSelectedPanel] = useState<StoryboardPanel | null>(null);

  const [fetching, setFetching] = useState(false);
  const [regeneratingPanelId, setRegeneratingPanelId] = useState<string | null>(null);
  const [regeneratingPage, setRegeneratingPage] = useState(false);
  const [renderingExternalPanelId, setRenderingExternalPanelId] = useState<string | null>(null);
  const [renderingExternalPage, setRenderingExternalPage] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (project.storyboard) {
      setStoryboardData(project.storyboard);
    }
  }, [project.storyboard]);

  useEffect(() => {
    if (activeTab !== 'presentation') return;
    const handleKeyDown = (e: KeyboardEvent) => {
      const totalPanels = storyboardData?.shot_plan?.panels?.length || 0;
      if (totalPanels === 0) return;
      if (e.key === 'ArrowLeft') {
        setPresentationIndex((prev) => Math.max(0, prev - 1));
      } else if (e.key === 'ArrowRight') {
        setPresentationIndex((prev) => Math.min(totalPanels - 1, prev + 1));
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeTab, storyboardData?.shot_plan?.panels?.length]);

  useEffect(() => {
    if (project.metadata?.id) {
      fetchVisualBible(project.metadata.id)
        .then((data) => setVisualBible(data))
        .catch(() => {});
    }
  }, [project.metadata?.id]);

  const handlePlanStoryboard = async () => {
    if (!project.screenplay) {
      setError('Screenplay must be generated first. Go to SCRIPT tab to transcribe simulation.');
      return;
    }
    setFetching(true);
    setError(null);
    try {
      const data = await planStoryboard(project.metadata.id, densityMode, 4);
      setStoryboardData(data);
      setActivePage(1);
      const bible = await fetchVisualBible(project.metadata.id);
      setVisualBible(bible);
    } catch (err: any) {
      setError(err.message || 'Failed to prepare storyboard shot plan');
    } finally {
      setFetching(false);
    }
  };

  const handleRegenerateSinglePanel = async (panelId: string, providerType?: string) => {
    setRegeneratingPanelId(panelId);
    setError(null);
    try {
      const res = await regeneratePanelVersion(project.metadata.id, panelId, providerType);
      if (storyboardData) {
        const newPanels = storyboardData.shot_plan.panels.map((p) =>
          p.id === panelId || p.panel_id === panelId ? res.panel : p
        );
        const newRenders = [...storyboardData.rendered_panels];
        if (res.panel_index >= 0 && res.panel_index < newRenders.length) {
          newRenders[res.panel_index] = res.rendered_panel;
        }
        const updated = {
          ...storyboardData,
          shot_plan: { ...storyboardData.shot_plan, panels: newPanels },
          rendered_panels: newRenders,
        };
        setStoryboardData(updated);
        if (selectedPanel && (selectedPanel.id === panelId || selectedPanel.panel_id === panelId)) {
          setSelectedPanel(res.panel);
        }
      }
    } catch (err: any) {
      setError(err.message || `Failed to regenerate panel ${panelId}`);
    } finally {
      setRegeneratingPanelId(null);
    }
  };

  const handleSelectVersion = async (panelId: string, version: number) => {
    try {
      const res = await selectPanelVersion(project.metadata.id, panelId, version);
      if (storyboardData) {
        const newPanels = storyboardData.shot_plan.panels.map((p) =>
          p.id === panelId || p.panel_id === panelId ? res.panel : p
        );
        setStoryboardData({
          ...storyboardData,
          shot_plan: { ...storyboardData.shot_plan, panels: newPanels },
        });
        setSelectedPanel(res.panel);
      }
    } catch (err: any) {
      setError(err.message || `Failed to switch version for panel ${panelId}`);
    }
  };

  const handleRegeneratePage = async (pageNumber: number) => {
    setRegeneratingPage(true);
    setError(null);
    try {
      const res = await regeneratePage(project.metadata.id, pageNumber);
      if (storyboardData) {
        setStoryboardData({
          ...storyboardData,
          rendered_panels: res.rendered_panels,
        });
      }
    } catch (err: any) {
      setError(err.message || `Failed to regenerate page ${pageNumber}`);
    } finally {
      setRegeneratingPage(false);
    }
  };

  const handleExternalRenderPanel = async (panelId: string) => {
    setRenderingExternalPanelId(panelId);
    setError(null);
    try {
      const res = await externalRenderPanel(project.metadata.id, panelId);
      if (storyboardData) {
        const newPanels = storyboardData.shot_plan.panels.map((p) =>
          p.id === panelId || p.panel_id === panelId ? res.panel : p
        );
        const newRenders = [...storyboardData.rendered_panels];
        if (res.panel_index >= 0 && res.panel_index < newRenders.length) {
          newRenders[res.panel_index] = res.rendered_panel;
        }
        const updated = {
          ...storyboardData,
          shot_plan: { ...storyboardData.shot_plan, panels: newPanels },
          rendered_panels: newRenders,
        };
        setStoryboardData(updated);
        if (selectedPanel && (selectedPanel.id === panelId || selectedPanel.panel_id === panelId)) {
          setSelectedPanel(res.panel);
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to render panel externally');
    } finally {
      setRenderingExternalPanelId(null);
    }
  };

  const handleExternalRenderPage = async (pageNumber: number) => {
    setRenderingExternalPage(true);
    setError(null);
    try {
      const res = await externalRenderPage(project.metadata.id, pageNumber);
      if (storyboardData) {
        setStoryboardData({
          ...storyboardData,
          shot_plan: res.shot_plan,
          rendered_panels: res.rendered_panels,
        });
      }
    } catch (err: any) {
      setError(err.message || 'Failed to render page externally');
    } finally {
      setRenderingExternalPage(false);
    }
  };

  const panels: StoryboardPanel[] = storyboardData?.shot_plan?.panels || [];
  const renderedPanels = storyboardData?.rendered_panels || [];
  const continuityReport: ContinuityReport | undefined = storyboardData?.continuity_report;

  const totalPages =
    storyboardData?.shot_plan?.total_pages ||
    (panels.length > 0 ? Math.max(...panels.map((p) => p.page_number || 1), 1) : 1);

  const pagePanels = panels.filter((p) => (p.page_number || 1) === activePage);
  const displayPanels = pagePanels.length > 0 ? pagePanels : panels;

  const currentPageObj = storyboardData?.shot_plan?.pages?.find((pg) => pg.page_number === activePage);
  const currentTemplate = currentPageObj?.layout_template || 'template_a';

  return (
    <div className="cinematic-storyboard-pane">
      {/* Top Header Controls */}
      <div className="pane-header">
        <div>
          <span className="pane-kicker">CINEMATIC PREPARATION &amp; GRAPHIC NOVEL BOARDS</span>
          <h2 className="pane-title">STORYBOARD</h2>
        </div>

        <div className="pane-actions" style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <div className="density-selector" title="Shot coverage density per scene">
            <span>DENSITY:</span>
            <select
              value={densityMode}
              onChange={(e) => setDensityMode(e.target.value)}
              disabled={fetching || regeneratingPage || renderingExternalPage}
            >
              <option value="quick">QUICK (2 / scene)</option>
              <option value="standard">STANDARD (4 / scene)</option>
              <option value="detailed">DETAILED (6-8 / scene)</option>
            </select>
          </div>

          {panels.length > 0 && (
            <>
              <button
                className="btn-cinematic-secondary"
                onClick={() => handleRegeneratePage(activePage)}
                disabled={regeneratingPage || fetching}
                title={`Regenerate all visual frames on Page ${activePage} (Offline Hand-Drawn)`}
              >
                {regeneratingPage ? 'REGENERATING PAGE...' : `↻ REGENERATE PAGE ${activePage}`}
              </button>

              <button
                className="btn-cinematic-secondary"
                onClick={() => handleExternalRenderPage(activePage)}
                disabled={renderingExternalPage || fetching}
                title="Optional external provider. Availability, quotas and pricing depend on the provider/account."
              >
                {renderingExternalPage ? 'RENDERING EXTERNALLY...' : `⚡ RENDER PAGE EXTERNALLY`}
              </button>
            </>
          )}

          <button
            className="btn-cinematic-primary"
            onClick={handlePlanStoryboard}
            disabled={fetching}
          >
            {fetching ? 'PLANNING FRAMES...' : 'PREPARE SHOT PLAN'}
          </button>
        </div>
      </div>

      {/* Sub-Navigation Tabs Bar */}
      <div className="storyboard-subtabs-bar">
        <div className="storyboard-subtabs">
          <button
            className={`subtab-btn ${activeTab === 'comic' ? 'active' : ''}`}
            onClick={() => setActiveTab('comic')}
          >
            📖 COMIC BOOK PAGES
          </button>
          <button
            className={`subtab-btn ${activeTab === 'grid' ? 'active' : ''}`}
            onClick={() => setActiveTab('grid')}
          >
            ▦ SHOT GRID
          </button>
          <button
            className={`subtab-btn ${activeTab === 'presentation' ? 'active' : ''}`}
            onClick={() => setActiveTab('presentation')}
          >
            🎬 PRESENTATION VIEW
          </button>
          <button
            className={`subtab-btn ${activeTab === 'bible' ? 'active' : ''}`}
            onClick={() => setActiveTab('bible')}
          >
            🎨 VISUAL BIBLE
          </button>
          {continuityReport && (
            <button
              className={`subtab-btn ${activeTab === 'continuity' ? 'active' : ''}`}
              onClick={() => setActiveTab('continuity')}
            >
              ⚖ CONTINUITY ({Math.round((continuityReport.score || 1) * 100)}%)
            </button>
          )}
        </div>

        {/* Multi-Page Navigation */}
        {panels.length > 0 && totalPages > 1 && (
          <div className="storyboard-page-bar" style={{ margin: 0, padding: 0, border: 'none' }}>
            <div className="page-nav-controls">
              <button
                className="page-nav-btn"
                onClick={() => setActivePage((prev) => Math.max(1, prev - 1))}
                disabled={activePage <= 1}
              >
                ◀ PREV
              </button>
              <span className="page-indicator">
                PAGE {activePage} OF {totalPages}
              </span>
              <button
                className="page-nav-btn"
                onClick={() => setActivePage((prev) => Math.min(totalPages, prev + 1))}
                disabled={activePage >= totalPages}
              >
                NEXT ▶
              </button>
            </div>

            <div className="page-tabs-list">
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((pg) => (
                <button
                  key={pg}
                  className={`page-tab-chip ${activePage === pg ? 'active' : ''}`}
                  onClick={() => setActivePage(pg)}
                >
                  PG {pg}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="modal-error-box" style={{ margin: '12px 0' }}>
          {error}
        </div>
      )}

      {/* Main Content Area */}
      <div className="storyboard-content-scroll">
        {panels.length === 0 ? (
          <div className="empty-quiet" style={{ marginTop: '60px' }}>
            NO SHOT PLAN PREPARED YET.<br />
            {project.screenplay ? (
              <span>CLICK <strong>PREPARE SHOT PLAN</strong> TO GENERATE CINEMATIC FRAMES.</span>
            ) : (
              <span>GENERATE A SCREENPLAY UNDER <strong>SCRIPT</strong> BEFORE PLANNING FRAMES.</span>
            )}
          </div>
        ) : (
          <>
            {/* 1. COMIC BOOK PAGES VIEW */}
            {activeTab === 'comic' && (
              <div className="comic-page-wrapper">
                <div className="comic-page-sheet">
                  <div className="comic-page-header">
                    <span className="comic-page-meta-title">
                      {project.metadata.title} // PAGE {activePage} OF {totalPages}
                    </span>
                    <span className="comic-page-meta-template">
                      LAYOUT: {String(currentTemplate).toUpperCase().replace('_', ' ')}
                    </span>
                  </div>

                  <div className={`comic-template-grid comic-${String(currentTemplate).replace('_', '-')}`}>
                    {displayPanels.map((panel) => {
                      const origIdx = panels.findIndex((p) => p.id === panel.id);
                      const renderData = origIdx >= 0 ? renderedPanels[origIdx] : null;
                      const svgContent = safeExtractSvg(renderData) || panel.rendered_svg;
                      const shotNum = panel.shot_number ?? panel.panel_number ?? 1;

                      const isAi =
                        (typeof renderData === 'object' && renderData?.mode === 'ai_image') ||
                        panel.versions?.some((v) => v.is_selected && v.mode === 'ai_image');
                      const isHandDrawn =
                        !isAi &&
                        ((typeof renderData === 'object' && (renderData?.mode === 'hand_drawn' || renderData?.provider === 'hand_drawn_storyboard')) ||
                          panel.versions?.some((v) => v.is_selected && (v.mode === 'hand_drawn' || v.provider === 'hand_drawn_storyboard')) ||
                          panel.provider === 'hand_drawn_storyboard' ||
                          panel.mode === 'hand_drawn' ||
                          !panel.fallback_reason);
                      const badgeLabel = isAi ? 'EXTERNAL AI IMAGE' : (isHandDrawn ? 'HAND-DRAWN STORYBOARD' : 'FALLBACK COMIC');
                      const badgeClass = isAi ? 'badge-ai-image' : (isHandDrawn ? 'badge-hand-drawn' : 'badge-fallback-comic');

                      const activeVer =
                        panel.selected_version ||
                        (typeof renderData === 'object' && renderData?.version) ||
                        1;

                      const slotClass = panel.layout_slot ? `slot-${panel.layout_slot}` : '';
                      const shotType = (panel.shot_type || 'medium').replace(/_/g, ' ').toUpperCase();
                      const cameraAngle = (panel.camera_angle || 'eye_level').replace(/_/g, ' ').toUpperCase();
                      const locName = formatDisplayValue(
                        panel.location_name ||
                        project.world?.locations?.[panel.location_id]?.name ||
                        panel.location_id ||
                        'Unknown Location'
                      );

                      let actorNames = '';
                      if (panel.character_names && Array.isArray(panel.character_names) && panel.character_names.length > 0) {
                        actorNames = formatDisplayValue(panel.character_names);
                      } else if (panel.characters_present && Array.isArray(panel.characters_present) && panel.characters_present.length > 0) {
                        actorNames = panel.characters_present
                          .map((cid) => formatDisplayValue(project.world?.characters?.[cid]?.name || cid))
                          .filter((s) => s !== '—')
                          .join(', ');
                      }

                      const actionText = formatDisplayValue(panel.action || panel.action_description || 'Scene unfolds');
                      const promptText = formatDisplayValue(panel.image_prompt || panel.prompt || panel.visual_prompt || '');
                      const imageUrl =
                        panel.image_url ||
                        (typeof renderData === 'object' ? renderData?.image_url : null);
                      const isRegenerating = regeneratingPanelId === panel.id;

                      return (
                        <div
                          key={panel.id || `comic-${shotNum}`}
                          className={`comic-panel-box ${slotClass}`}
                          onClick={() => setSelectedPanel(panel)}
                          title="Click to open Panel Inspector, view version history, or regenerate"
                        >
                          {/* Top Bar inside panel */}
                          <div className="panel-card-topbar" style={{ background: '#0a0d14', borderBottom: '1px solid #27272a', padding: '6px 10px' }}>
                            <span className="frame-number-badge" style={{ position: 'static' }}>
                              SHOT {String(shotNum).padStart(2, '0')} • SCENE {panel.scene_number || 1}
                            </span>
                            <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                              <span className="panel-badge text-amber">{shotType}</span>
                              <span className="panel-badge">{cameraAngle}</span>
                              <span className="badge-pill badge-version">v{activeVer}</span>
                              <span className={`badge-pill ${badgeClass}`}>
                                {badgeLabel}
                              </span>
                              {!isAi && !isHandDrawn && panel.fallback_reason && (
                                <span className="badge-pill" style={{ background: '#451a03', color: '#fca5a5', fontSize: '9px', border: '1px solid #78350f' }} title={`Fallback: ${panel.fallback_reason}`}>
                                  {panel.fallback_reason}
                                </span>
                              )}
                              <button
                                className="btn-panel-regen"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleRegenerateSinglePanel(panel.id);
                                }}
                                disabled={isRegenerating}
                                title="Regenerate this specific visual panel"
                              >
                                {isRegenerating ? '↻...' : '↻'}
                              </button>
                            </div>
                          </div>

                          {/* Art Layer Container */}
                          <div style={{ position: 'relative', width: '100%', height: 'calc(100% - 32px)', minHeight: '200px' }}>
                            {imageUrl && !imageUrl.endsWith('.svg') ? (
                              <img
                                src={imageUrl}
                                alt={panel.caption || `Shot ${shotNum}`}
                                className="comic-panel-artwork"
                                loading="lazy"
                              />
                            ) : svgContent ? (
                              <div
                                className="comic-svg-art"
                                dangerouslySetInnerHTML={{ __html: svgContent }}
                              />
                            ) : (
                              <div className="storyboard-placeholder-sketch">
                                <span className="sketch-crosshair">✛</span>
                                <span className="sketch-label">SHOT {shotNum}</span>
                              </div>
                            )}

                            {/* SFX Burst Overlay */}
                            {panel.sfx_label && (
                              <div className="comic-sfx-burst">
                                {panel.sfx_label}
                              </div>
                            )}

                            {/* Speech / Caption Overlays */}
                            <div className="comic-bubble-container">
                              {panel.dialogue_excerpt && (
                                <div className="comic-bubble-top-slot">
                                  <div
                                    className={
                                      panel.dialogue_bubble_type === 'whisper'
                                        ? 'comic-speech-bubble comic-whisper-bubble'
                                        : panel.dialogue_bubble_type === 'shout'
                                        ? 'comic-speech-bubble comic-shout-bubble'
                                        : panel.dialogue_bubble_type === 'thought'
                                        ? 'comic-speech-bubble comic-thought-bubble'
                                        : 'comic-speech-bubble'
                                    }
                                  >
                                    "{panel.dialogue_excerpt}"
                                  </div>
                                </div>
                              )}

                              <div className="comic-bubble-bottom-slot">
                                <div className="comic-caption-strip">
                                  {panel.caption || panel.action_description || panel.action}
                                </div>
                              </div>
                            </div>
                          </div>

                          {/* Collapsible details for tests & technical users */}
                          <div style={{ padding: '8px 12px', background: '#0a0d14', borderTop: '1px solid #1e293b', fontSize: '11px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                              {actorNames && (
                                <div>
                                  <span className="text-muted">ACTORS: </span>
                                  <span>{actorNames}</span>
                                </div>
                              )}
                              <span className="panel-location-tag">📍 {locName}</span>
                            </div>
                            <div style={{ color: '#cbd5e1', marginBottom: '4px' }}>
                              <span className="text-muted">ACTION: </span>
                              <span>{actionText}</span>
                            </div>
                            <details className="panel-prompt-details">
                              <summary className="panel-prompt-summary">PROMPT &amp; DETAILS</summary>
                              <div className="panel-prompt-mono">{promptText}</div>
                            </details>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            {/* 2. SHOT GRID VIEW */}
            {activeTab === 'grid' && (
              <div className="storyboard-panels-grid">
                {displayPanels.map((panel) => {
                  const originalIndex = panels.findIndex((p) => p.id === panel.id);
                  const renderData = originalIndex >= 0 ? renderedPanels[originalIndex] : null;
                  const svgContent = safeExtractSvg(renderData) || panel.rendered_svg;
                  const shotNum = panel.shot_number ?? panel.panel_number ?? 1;

                  const isAi =
                    (typeof renderData === 'object' && renderData?.mode === 'ai_image') ||
                    panel.versions?.some((v) => v.is_selected && v.mode === 'ai_image');
                  const isHandDrawn =
                    !isAi &&
                    ((typeof renderData === 'object' && (renderData?.mode === 'hand_drawn' || renderData?.provider === 'hand_drawn_storyboard')) ||
                      panel.versions?.some((v) => v.is_selected && (v.mode === 'hand_drawn' || v.provider === 'hand_drawn_storyboard')) ||
                      panel.provider === 'hand_drawn_storyboard' ||
                      panel.mode === 'hand_drawn' ||
                      !panel.fallback_reason);
                  const badgeLabel = isAi ? 'EXTERNAL AI IMAGE' : (isHandDrawn ? 'HAND-DRAWN STORYBOARD' : 'FALLBACK COMIC');
                  const badgeClass = isAi ? 'badge-ai-image' : (isHandDrawn ? 'badge-hand-drawn' : 'badge-fallback-comic');

                  const activeVer =
                    panel.selected_version ||
                    (typeof renderData === 'object' && renderData?.version) ||
                    1;

                  const shotType = (panel.shot_type || 'medium').replace(/_/g, ' ').toUpperCase();
                  const cameraAngle = (panel.camera_angle || 'eye_level').replace(/_/g, ' ').toUpperCase();
                  const locName = formatDisplayValue(
                    panel.location_name ||
                    project.world?.locations?.[panel.location_id]?.name ||
                    panel.location_id ||
                    'Unknown Location'
                  );

                  let actorNames = '';
                  if (panel.character_names && Array.isArray(panel.character_names) && panel.character_names.length > 0) {
                    actorNames = formatDisplayValue(panel.character_names);
                  } else if (panel.characters_present && Array.isArray(panel.characters_present) && panel.characters_present.length > 0) {
                    actorNames = panel.characters_present
                      .map((cid) => formatDisplayValue(project.world?.characters?.[cid]?.name || cid))
                      .filter((s) => s !== '—')
                      .join(', ');
                  }

                  const actionText = formatDisplayValue(panel.action || panel.action_description || 'Scene unfolds');
                  const dialogueText = panel.dialogue_excerpt ? formatDisplayValue(panel.dialogue_excerpt) : null;
                  const promptText = formatDisplayValue(panel.image_prompt || panel.prompt || panel.visual_prompt || '');
                  const sourceBlocks = panel.source_screenplay_block_ids || [];
                  const isRegenerating = regeneratingPanelId === panel.id;
                  const imageUrl =
                    panel.image_url ||
                    (typeof renderData === 'object' ? renderData?.image_url : null);

                    return (
                    <div
                      key={panel.id || `grid-${shotNum}`}
                      className="noir-storyboard-panel artwork-first-card"
                      onClick={() => setSelectedPanel(panel)}
                      title="Click to open Panel Inspector, view version history, or inspect continuity"
                    >
                      <div className="panel-card-topbar-clean">
                        <span className="frame-number-badge" style={{ position: 'static' }}>
                          SHOT {String(shotNum).padStart(2, '0')} • {shotType}{cameraAngle ? ` / ${cameraAngle}` : ''}
                        </span>

                        <div style={{ display: 'flex', gap: '5px', alignItems: 'center', flexWrap: 'wrap' }}>
                          {panel.transition_type && (
                            <span className="panel-badge text-amber" title={panel.visual_link ? `Visual link: ${panel.visual_link}` : undefined}>
                              ⤹ {panel.transition_type.replace(/_/g, ' ').toUpperCase()}
                            </span>
                          )}
                          {panel.camera_movement && (
                            <span className="panel-badge" title="Camera Movement">
                              🎥 {panel.camera_movement.replace(/_/g, ' ').toUpperCase()}
                            </span>
                          )}
                          <span className="panel-badge text-amber">{shotType}</span>
                          <span className="panel-badge">{cameraAngle}</span>
                          <span className="badge-pill badge-version">v{activeVer}</span>
                          <span className={`badge-pill ${badgeClass}`}>
                            {badgeLabel}
                          </span>
                          {!isAi && !isHandDrawn && panel.fallback_reason && (
                            <span className="badge-pill" style={{ background: '#451a03', color: '#fca5a5', fontSize: '9px', border: '1px solid #78350f' }} title={`Fallback: ${panel.fallback_reason}`}>
                              {panel.fallback_reason}
                            </span>
                          )}
                          <button
                            className="btn-panel-regen"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRegenerateSinglePanel(panel.id);
                            }}
                            disabled={isRegenerating}
                            title="Regenerate this specific visual panel"
                          >
                            {isRegenerating ? '↻...' : '↻'}
                          </button>
                        </div>
                      </div>

                      {/* 16:9 Cinematic Artwork Frame (75-80% card prominence) */}
                      <div className="storyboard-frame-container artwork-first-frame">
                        {imageUrl && !imageUrl.endsWith('.svg') ? (
                          <img
                            src={imageUrl}
                            alt={panel.caption || `Shot ${shotNum}`}
                            className="comic-panel-artwork"
                            loading="lazy"
                          />
                        ) : svgContent ? (
                          <div
                            className="storyboard-svg-wrapper"
                            dangerouslySetInnerHTML={{ __html: svgContent }}
                          />
                        ) : (
                          <div className="storyboard-placeholder-sketch">
                            <span className="sketch-crosshair">✛</span>
                            <span className="sketch-label">FRAME {String(shotNum).padStart(2, '0')}</span>
                          </div>
                        )}
                      </div>

                      {/* Clean Artwork-First Action & Subject Bar */}
                      <div className="panel-info-compact">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div className="panel-chars-chips">
                            {panel.character_names && panel.character_names.length > 0
                              ? panel.character_names.map((cName) => (
                                  <span key={cName} className="char-chip">👤 {cName}</span>
                                ))
                              : actorNames ? <span className="char-chip">👤 {actorNames}</span> : null}
                            {panel.objects_in_frame && panel.objects_in_frame.length > 0 && (
                              <span className="prop-chip">📦 {panel.objects_in_frame.join(', ')}</span>
                            )}
                          </div>
                          <span className="panel-location-tag">📍 {locName}</span>
                        </div>

                        <p className="panel-action-desc-clean">
                          {actionText}
                        </p>

                        {dialogueText && (
                          <div className="panel-dialogue-excerpt">
                            "{dialogueText}"
                          </div>
                        )}

                        <details className="panel-prompt-details" onClick={(e) => e.stopPropagation()}>
                          <summary className="panel-prompt-summary">PROMPT &amp; DETAILS</summary>
                          <div className="panel-prompt-mono">
                            <div className="mono-kicker">IMAGE GENERATION PROMPT PACKAGE</div>
                            <div>{promptText}</div>
                            {panel.negative_prompt && (
                              <div style={{ marginTop: '4px' }}>
                                <span className="mono-kicker">NEGATIVE PROMPT: </span>
                                <span className="text-muted">{panel.negative_prompt}</span>
                              </div>
                            )}
                            {sourceBlocks.length > 0 && (
                              <div style={{ marginTop: '4px', opacity: 0.75 }}>
                                <span className="mono-kicker">SCENE BLOCKS: </span>
                                <span>{sourceBlocks.join(', ')}</span>
                              </div>
                            )}
                          </div>
                        </details>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* 3. PRESENTATION / DIRECTOR VIEW MODE */}
            {activeTab === 'presentation' && panels.length > 0 && (
              <div className="presentation-view-container">
                {(() => {
                  const currentIdx = Math.max(0, Math.min(panels.length - 1, presentationIndex));
                  const panel = panels[currentIdx];
                  const renderData = currentIdx < renderedPanels.length ? renderedPanels[currentIdx] : null;
                  const svgContent = safeExtractSvg(renderData) || panel.rendered_svg;
                  const shotNum = panel.shot_number ?? panel.panel_number ?? currentIdx + 1;
                  const imageUrl = panel.image_url || (typeof renderData === 'object' ? renderData?.image_url : null);
                  const isRegenerating = regeneratingPanelId === panel.id;

                  const shotType = (panel.shot_type || 'medium').replace(/_/g, ' ').toUpperCase();
                  const cameraAngle = (panel.camera_angle || 'eye_level').replace(/_/g, ' ').toUpperCase();
                  const locName = formatDisplayValue(
                    panel.location_name ||
                    project.world?.locations?.[panel.location_id]?.name ||
                    panel.location_id ||
                    'Scene Setting'
                  );
                  const actionText = formatDisplayValue(panel.action || panel.action_description || 'Scene unfolds');
                  const dialogueText = panel.dialogue_excerpt ? formatDisplayValue(panel.dialogue_excerpt) : null;

                  return (
                    <>
                      {/* Presentation Controls Bar */}
                      <div className="presentation-controls-bar">
                        <button
                          className="page-nav-btn"
                          onClick={() => setPresentationIndex((prev) => Math.max(0, prev - 1))}
                          disabled={currentIdx <= 0}
                          title="Previous shot (Left Arrow)"
                        >
                          ◀ PREV SHOT
                        </button>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <span className="page-indicator" style={{ fontSize: '13px', fontWeight: 800 }}>
                            SHOT {String(shotNum).padStart(2, '0')} OF {panels.length} • SCENE {panel.scene_number || 1}
                          </span>
                          <span className="panel-badge text-amber">{shotType}</span>
                          <span className="panel-badge">{cameraAngle}</span>
                        </div>

                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button
                            className="btn-cinematic-secondary"
                            onClick={() => setSelectedPanel(panel)}
                          >
                            🔍 INSPECT PANEL
                          </button>
                          <button
                            className="btn-cinematic-secondary"
                            onClick={() => handleRegenerateSinglePanel(panel.id)}
                            disabled={isRegenerating}
                          >
                            {isRegenerating ? '↻...' : '↻ REGENERATE'}
                          </button>
                          <button
                            className="page-nav-btn"
                            onClick={() => setPresentationIndex((prev) => Math.min(panels.length - 1, prev + 1))}
                            disabled={currentIdx >= panels.length - 1}
                            title="Next shot (Right Arrow)"
                          >
                            NEXT SHOT ▶
                          </button>
                        </div>
                      </div>

                      {/* Large 16:9 Cinematic Stage */}
                      <div className="presentation-stage" onClick={() => setSelectedPanel(panel)}>
                        {imageUrl && !imageUrl.endsWith('.svg') ? (
                          <img
                            src={imageUrl}
                            alt={panel.caption || `Shot ${shotNum}`}
                            className="comic-panel-artwork"
                            loading="lazy"
                          />
                        ) : svgContent ? (
                          <div
                            className="storyboard-svg-wrapper"
                            dangerouslySetInnerHTML={{ __html: svgContent }}
                          />
                        ) : (
                          <div className="storyboard-placeholder-sketch">
                            <span className="sketch-crosshair">✛</span>
                            <span className="sketch-label">SHOT {shotNum}</span>
                          </div>
                        )}
                      </div>

                      {/* Director's Notes Block */}
                      <div className="presentation-director-notes">
                        <div className="presentation-shot-title">
                          <div>
                            <span className="pane-kicker">DIRECTOR'S NOTEBOOK</span>
                            <h3 style={{ margin: '4px 0 0 0', color: '#f8fafc', fontSize: '16px' }}>
                              SHOT {String(shotNum).padStart(2, '0')} // {panel.narrative_purpose?.toUpperCase() || 'ACTION'}
                            </h3>
                          </div>
                          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                            <span className="panel-location-tag" style={{ fontSize: '12px' }}>
                              📍 {locName}
                            </span>
                            <span className="text-muted" style={{ fontSize: '11px' }}>
                              Use ◀ / ▶ keys to navigate
                            </span>
                          </div>
                        </div>

                        {panel.transition_type && (
                          <div className="presentation-transition-banner" style={{ background: 'rgba(245, 158, 11, 0.12)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: '4px', padding: '8px 12px', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                            <span style={{ fontSize: '12px', fontWeight: 800, color: '#f59e0b' }}>
                              ⤹ TRANSITION: {panel.transition_type.replace(/_/g, ' ').toUpperCase()}
                            </span>
                            {panel.visual_link && (
                              <span style={{ fontSize: '12px', color: '#cbd5e1' }}>
                                • Visual link: <em style={{ color: '#fde68a' }}>{panel.visual_link}</em>
                              </span>
                            )}
                          </div>
                        )}

                        <div className="presentation-action-hero">
                          {actionText}
                        </div>

                        {dialogueText && (
                          <div className="panel-dialogue-excerpt" style={{ fontSize: '13px', padding: '6px 12px' }}>
                            "{dialogueText}"
                          </div>
                        )}

                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '6px' }}>
                          <span className="panel-badge text-amber">{shotType}</span>
                          <span className="panel-badge">{cameraAngle}</span>
                          {panel.camera_movement && (
                            <span className="panel-badge text-amber">🎥 {panel.camera_movement.replace(/_/g, ' ').toUpperCase()}</span>
                          )}
                          {panel.focal_depth_plane && (
                            <span className="panel-badge">Depth: {panel.focal_depth_plane.replace(/_/g, ' ').toUpperCase()}</span>
                          )}
                          {panel.lighting_profile_id && (
                            <span className="panel-badge">Light: {panel.lighting_profile_id.replace(/_/g, ' ').toUpperCase()}</span>
                          )}
                          {panel.lens_feel && <span className="panel-badge">{panel.lens_feel}</span>}
                          {panel.composition && (
                            <span className="panel-badge">Framing: {panel.composition}</span>
                          )}
                          {panel.lighting && !panel.lighting_profile_id && (
                            <span className="panel-badge">Light: {panel.lighting}</span>
                          )}
                        </div>

                        {panel.objects_in_frame && panel.objects_in_frame.length > 0 && (
                          <div style={{ fontSize: '12px', color: '#94a3b8' }}>
                            <strong style={{ color: '#cbd5e1' }}>Props in Frame:</strong>{' '}
                            <span className="text-amber">{panel.objects_in_frame.join(', ')}</span>
                          </div>
                        )}

                        {panel.continuity_notes && (
                          <div className="panel-continuity-note" style={{ fontSize: '11px' }}>
                            <span className="continuity-icon">🔗 CONTINUITY: </span>
                            <span>{panel.continuity_notes}</span>
                          </div>
                        )}
                      </div>
                    </>
                  );
                })()}
              </div>
            )}

            {/* 3. VISUAL BIBLE VIEW */}
            {activeTab === 'bible' && visualBible && (
              <div className="visual-bible-container">
                <div>
                  <div className="bible-section-title">✦ AESTHETIC &amp; STYLE PROFILE</div>
                  <div className="bible-card" style={{ borderLeft: '4px solid var(--accent-amber)' }}>
                    <div className="bible-card-header">
                      <div>
                        <div className="bible-title">{visualBible.style_profile?.name || 'Cinematic Graphic Novel'}</div>
                        <div className="bible-subtitle">{visualBible.style_profile?.medium}</div>
                      </div>
                      <span className="badge-pill badge-ai-image">ACTIVE STYLE</span>
                    </div>
                    <div className="bible-prop-row">
                      <span className="bible-prop-label">LINEWORK: </span>
                      <span>{visualBible.style_profile?.linework}</span>
                    </div>
                    <div className="bible-prop-row">
                      <span className="bible-prop-label">LIGHTING: </span>
                      <span>{visualBible.style_profile?.lighting_style}</span>
                    </div>
                    <div className="bible-prop-row">
                      <span className="bible-prop-label">PALETTE: </span>
                      <span>{visualBible.style_profile?.color_palette}</span>
                    </div>
                    <div className="bible-prop-row">
                      <span className="bible-prop-label">INFLUENCES: </span>
                      <span>{visualBible.style_profile?.artist_influences?.join(', ')}</span>
                    </div>
                  </div>

                  <div className="bible-card" style={{ borderLeft: '4px solid #38bdf8', marginTop: '12px' }}>
                    <div className="bible-card-header">
                      <div>
                        <div className="bible-title">CONTINUITY ENGINE CONFIGURATION</div>
                        <div className="bible-subtitle">Character &amp; World Consistency Pipeline</div>
                      </div>
                      <span className="badge-pill badge-continuity-mode">
                        TEXTUAL CONTINUITY ONLY
                      </span>
                    </div>
                    <div className="bible-prop-row">
                      <span className="bible-prop-label">PROVIDER: </span>
                      <span>Google Generative Language API (imagen-3.0-generate-002)</span>
                    </div>
                    <div className="bible-prop-row">
                      <span className="bible-prop-label">CONDITIONING: </span>
                      <span>No reference-image or latent conditioning API supported on Google AI Studio endpoint. Consistency enforced via compiled multi-layer prompt turnarounds &amp; canonical object/character anchors.</span>
                    </div>
                  </div>
                </div>

                <div>
                  <div className="bible-section-title">👤 CANONICAL ACTORS &amp; WARDROBE</div>
                  <div className="bible-grid">
                    {Object.values(visualBible.characters || {}).map((char) => (
                      <div key={char.character_id} className="bible-card">
                        <div className="bible-card-header">
                          <div>
                            <div className="bible-title">{char.name}</div>
                            <div className="bible-subtitle">{char.role || 'Protagonist'} • {char.age}</div>
                          </div>
                        </div>
                        <div className="bible-prop-row">
                          <span className="bible-prop-label">FACE: </span>
                          <span>{char.face_features}</span>
                        </div>
                        <div className="bible-prop-row">
                          <span className="bible-prop-label">HAIR: </span>
                          <span>{char.hair}</span>
                        </div>
                        <div className="bible-prop-row">
                          <span className="bible-prop-label">WARDROBE: </span>
                          <span>{char.clothing}</span>
                        </div>
                        {char.signature_props && char.signature_props.length > 0 && (
                          <div className="bible-prop-row">
                            <span className="bible-prop-label">SIGNATURE PROPS: </span>
                            <span className="text-amber">{char.signature_props.join(', ')}</span>
                          </div>
                        )}
                        <div className="bible-prop-row">
                          <span className="bible-prop-label">EXPRESSION: </span>
                          <span>{char.expression_tendency}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <div className="bible-section-title">🗝 KEY STORY PROPS</div>
                  <div className="bible-grid">
                    {Object.values(visualBible.objects || {}).map((obj) => (
                      <div key={obj.object_id} className="bible-card">
                        <div className="bible-card-header">
                          <div className="bible-title">{obj.name}</div>
                          <span className="bible-subtitle">{obj.form_factor}</span>
                        </div>
                        <div className="bible-prop-row">
                          <span className="bible-prop-label">MATERIALS: </span>
                          <span>{obj.materials}</span>
                        </div>
                        <div className="bible-prop-row">
                          <span className="bible-prop-label">COLORS: </span>
                          <span>{obj.colors}</span>
                        </div>
                        <div className="bible-prop-row">
                          <span className="bible-prop-label">UNIQUE MARKERS: </span>
                          <span>{obj.unique_markings}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <div className="bible-section-title">📍 ENVIRONMENTS &amp; SETTINGS</div>
                  <div className="bible-grid">
                    {Object.values(visualBible.locations || {}).map((loc) => (
                      <div key={loc.location_id} className="bible-card">
                        <div className="bible-card-header">
                          <div className="bible-title">{loc.name}</div>
                          <span className="bible-subtitle">{loc.environment_type}</span>
                        </div>
                        <div className="bible-prop-row">
                          <span className="bible-prop-label">ARCHITECTURE: </span>
                          <span>{loc.architecture}</span>
                        </div>
                        <div className="bible-prop-row">
                          <span className="bible-prop-label">LIGHTING SETUP: </span>
                          <span>{loc.lighting_setup}</span>
                        </div>
                        <div className="bible-prop-row">
                          <span className="bible-prop-label">PALETTE: </span>
                          <span>{loc.color_palette}</span>
                        </div>
                        <div className="bible-prop-row">
                          <span className="bible-prop-label">MOOD: </span>
                          <span>{loc.mood}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* 4. CONTINUITY REPORT VIEW */}
            {activeTab === 'continuity' && continuityReport && (
              <div className="continuity-report-container">
                <div className="continuity-score-hero">
                  <div className="continuity-score-circle">
                    {Math.round(continuityReport.score * 100)}%
                  </div>
                  <div>
                    <h3 style={{ margin: '0 0 6px 0', fontSize: '18px', color: '#f8fafc' }}>
                      CONTINUITY &amp; VISUAL RHYTHM AUDIT
                    </h3>
                    <p style={{ margin: 0, fontSize: '13px', color: '#94a3b8' }}>
                      Deterministic check verifying character wardrobe stability, key prop tracking,
                      environmental lighting palettes, and camera framing variety across {continuityReport.total_panels} shots.
                    </p>
                    <div style={{ display: 'flex', gap: '16px', marginTop: '12px' }}>
                      <span className="panel-badge">
                        VARIETY: {Math.round(continuityReport.shot_variety_score * 100)}%
                      </span>
                      <span className="panel-badge">
                        CHARACTERS: {Math.round(continuityReport.character_consistency_score * 100)}%
                      </span>
                      <span className="panel-badge">
                        PROPS: {Math.round(continuityReport.prop_tracking_score * 100)}%
                      </span>
                    </div>
                  </div>
                </div>

                <div className="bible-section-title">CONTINUITY NOTICES &amp; SUGGESTIONS</div>
                {continuityReport.issues?.length === 0 ? (
                  <div className="bible-card" style={{ color: '#22c55e', fontWeight: 600 }}>
                    ✓ Perfect continuity verified across all sequence panels. No pacing or prop discrepancies detected.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {continuityReport.issues.map((issue, idx) => (
                      <div key={idx} className={`continuity-issue-card ${issue.severity}`}>
                        <div>
                          <span className="badge-pill" style={{ background: '#1e293b', color: '#f59e0b' }}>
                            {issue.category.toUpperCase()}
                          </span>
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: '13px', fontWeight: 600, color: '#f1f5f9', marginBottom: '4px' }}>
                            {issue.message}
                          </div>
                          <div style={{ fontSize: '12px', color: '#94a3b8' }}>
                            <span className="text-amber">Recommendation: </span>
                            {issue.suggestion}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {/* PANEL INSPECTOR MODAL */}
      {selectedPanel && (
        <div className="panel-inspector-overlay" onClick={() => setSelectedPanel(null)}>
          <div className="panel-inspector-modal" onClick={(e) => e.stopPropagation()}>
            <div className="inspector-header">
              <div>
                <span className="pane-kicker">PANEL INSPECTOR &amp; VERSION CONTROLLER</span>
                <h3 style={{ margin: '4px 0 0 0', color: '#f8fafc', fontSize: '16px' }}>
                  SHOT {selectedPanel.shot_number || selectedPanel.panel_number} // SCENE {selectedPanel.scene_number} ({selectedPanel.narrative_purpose?.toUpperCase()})
                </h3>
              </div>

              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  className="btn-cinematic-secondary"
                  onClick={() => handleRegenerateSinglePanel(selectedPanel.id, 'cloud')}
                  disabled={regeneratingPanelId === selectedPanel.id}
                >
                  {regeneratingPanelId === selectedPanel.id ? 'GENERATING...' : '★ REGENERATE (CLOUD AI)'}
                </button>
                <button
                  className="btn-cinematic-secondary"
                  onClick={() => handleRegenerateSinglePanel(selectedPanel.id, 'fallback')}
                  disabled={regeneratingPanelId === selectedPanel.id}
                >
                  ↻ REGENERATE (FALLBACK INKS)
                </button>
                <button
                  className="page-nav-btn"
                  onClick={() => setSelectedPanel(null)}
                >
                  ✕
                </button>
              </div>
            </div>

            <div className="inspector-body">
              <div>
                <div className="inspector-preview-box">
                  {selectedPanel.image_url && !selectedPanel.image_url.endsWith('.svg') ? (
                    <img
                      src={selectedPanel.image_url}
                      alt={selectedPanel.caption}
                      loading="lazy"
                    />
                  ) : selectedPanel.rendered_svg ? (
                    <div
                      className="storyboard-svg-wrapper"
                      dangerouslySetInnerHTML={{ __html: selectedPanel.rendered_svg }}
                    />
                  ) : (
                    <div className="storyboard-placeholder-sketch">
                      <span className="sketch-crosshair">✛</span>
                      <span className="sketch-label">NO IMAGE LOADED</span>
                    </div>
                  )}
                </div>

                <div style={{ marginTop: '16px' }}>
                  <div className="pane-kicker" style={{ marginBottom: '8px' }}>
                    GENERATION VERSIONS ({selectedPanel.versions?.length || 1})
                  </div>
                  <div style={{ display: 'flex', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
                    <button
                      className="btn-cinematic-secondary"
                      onClick={() => handleRegenerateSinglePanel(selectedPanel.id)}
                      disabled={regeneratingPanelId === selectedPanel.id}
                      title="Regenerate hand-drawn sketch (offline)"
                      style={{ padding: '6px 12px', fontSize: '11px' }}
                    >
                      {regeneratingPanelId === selectedPanel.id ? 'REGENERATING...' : '↻ REGENERATE HAND-DRAWN'}
                    </button>
                    <button
                      className="btn-cinematic-secondary"
                      onClick={() => handleExternalRenderPanel(selectedPanel.id)}
                      disabled={renderingExternalPanelId === selectedPanel.id}
                      title="Optional external provider. Availability, quotas and pricing depend on the provider/account."
                      style={{ padding: '6px 12px', fontSize: '11px', borderColor: '#7c3aed', color: '#c4b5fd' }}
                    >
                      {renderingExternalPanelId === selectedPanel.id ? 'RENDERING EXTERNALLY...' : '⚡ RENDER THIS PANEL EXTERNALLY'}
                    </button>
                  </div>
                  <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: '10px', fontStyle: 'italic' }}>
                    Optional external provider. Availability, quotas and pricing depend on the provider/account.
                  </div>
                  <div className="inspector-versions-list">
                    {(selectedPanel.versions && selectedPanel.versions.length > 0
                      ? selectedPanel.versions
                      : [
                          {
                            version: 1,
                            image_url: selectedPanel.image_url || '',
                            provider: selectedPanel.provider || 'procedural',
                            mode: (selectedPanel as any).mode || 'fallback_comic',
                            is_selected: true,
                          },
                        ]
                    ).map((ver) => (
                      <div
                        key={ver.version}
                        className={`version-chip ${ver.is_selected || selectedPanel.selected_version === ver.version ? 'active' : ''}`}
                        onClick={() => handleSelectVersion(selectedPanel.id, ver.version)}
                      >
                        <div className="version-thumb">
                          <span style={{ fontSize: '10px', color: '#94a3b8' }}>VER {ver.version}</span>
                        </div>
                        <div style={{ fontWeight: 800 }}>VERSION {ver.version}</div>
                        <div style={{ fontSize: '9px', color: ver.mode === 'ai_image' ? '#a78bfa' : (ver.mode === 'hand_drawn' ? '#38bdf8' : '#f59e0b') }}>
                          {ver.mode === 'ai_image' ? 'EXTERNAL AI' : (ver.mode === 'hand_drawn' ? 'HAND-DRAWN' : 'FALLBACK')}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {(() => {
                const currentVersion = selectedPanel.versions?.find(
                  (v) => (selectedPanel.selected_version ? v.version === selectedPanel.selected_version : v.is_selected)
                ) || selectedPanel.versions?.[selectedPanel.versions.length - 1];

                const isAiMode = currentVersion?.mode === 'ai_image' || (selectedPanel as any).mode === 'ai_image';
                const isHandDrawnMode =
                  !isAiMode &&
                  (currentVersion?.mode === 'hand_drawn' ||
                    currentVersion?.provider === 'hand_drawn_storyboard' ||
                    selectedPanel.provider === 'hand_drawn_storyboard' ||
                    (selectedPanel as any).mode === 'hand_drawn' ||
                    !currentVersion?.fallback_reason);

                const currentReason = isHandDrawnMode ? null : (currentVersion?.fallback_reason || selectedPanel.fallback_reason);
                const currentContinuity = currentVersion?.continuity_mode || selectedPanel.continuity_mode || 'Deterministic Visual Bible';
                const currentProvider = isHandDrawnMode
                  ? 'HandDrawnStoryboardProvider'
                  : (currentVersion?.provider || selectedPanel.provider || 'CloudImagenStoryboardProvider');
                const currentStyle = (currentVersion?.render_metadata?.style as string) || 'Pencil Noir';

                return (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    {/* Render Diagnostics */}
                    <div
                      style={{
                        padding: '12px 14px',
                        borderRadius: '4px',
                        background: isAiMode
                          ? 'rgba(124, 58, 237, 0.12)'
                          : isHandDrawnMode
                          ? 'rgba(2, 132, 199, 0.12)'
                          : 'rgba(245, 158, 11, 0.08)',
                        border: `1px solid ${
                          isAiMode
                            ? 'rgba(167, 139, 250, 0.4)'
                            : isHandDrawnMode
                            ? 'rgba(56, 189, 248, 0.4)'
                            : 'rgba(245, 158, 11, 0.35)'
                        }`,
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '8px',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
                        <span style={{ fontSize: '11px', fontWeight: 800, letterSpacing: '0.08em', color: '#94a3b8' }}>
                          RENDER DIAGNOSTICS
                        </span>
                        <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' }}>
                          <span
                            className={`badge-pill ${
                              isAiMode
                                ? 'badge-ai-image'
                                : isHandDrawnMode
                                ? 'badge-hand-drawn'
                                : 'badge-fallback-comic'
                            }`}
                          >
                            SOURCE: {isAiMode ? 'EXTERNAL AI IMAGE' : isHandDrawnMode ? 'HAND-DRAWN STORYBOARD' : 'FALLBACK COMIC'}
                          </span>
                          {currentReason && (
                            <span className="badge-pill badge-fallback-reason">
                              REASON: {currentReason}
                            </span>
                          )}
                        </div>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px' }}>
                        <span style={{ color: '#94a3b8' }}>RENDERER:</span>
                        <span style={{ color: '#cbd5e1', fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                          {currentProvider}
                        </span>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px' }}>
                        <span style={{ color: '#94a3b8' }}>STYLE:</span>
                        <span style={{ color: '#f59e0b', fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 600 }}>
                          {currentStyle}
                        </span>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px' }}>
                        <span style={{ color: '#94a3b8' }}>CONTINUITY:</span>
                        <span className="badge-pill badge-continuity-mode">
                          {currentContinuity}
                        </span>
                      </div>

                      {isHandDrawnMode && (
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px' }}>
                          <span style={{ color: '#94a3b8' }}>CLOUD API:</span>
                          <span style={{ color: '#38bdf8', fontSize: '11px', fontWeight: 600 }}>
                            NO CLOUD API (100% Offline SVG)
                          </span>
                        </div>
                      )}

                      {currentReason === 'QUOTA_EXCEEDED' && (
                        <div
                          style={{
                            fontSize: '11px',
                            color: '#fca5a5',
                            marginTop: '4px',
                            background: 'rgba(239, 68, 68, 0.12)',
                            padding: '6px 10px',
                            borderRadius: '4px',
                            border: '1px solid rgba(239, 68, 68, 0.25)',
                            lineHeight: 1.4,
                          }}
                        >
                          ⚠ Cloud image generation unavailable because this Google project currently has no usable quota for the selected image model.
                        </div>
                      )}
                    </div>

                    <div>
                      <div className="pane-kicker">CINEMATIC TECHNICAL SPECS</div>
                      <div style={{ display: 'flex', gap: '6px', marginTop: '6px', flexWrap: 'wrap' }}>
                        <span className="panel-badge text-amber">{selectedPanel.shot_type.toUpperCase()}</span>
                        <span className="panel-badge">{selectedPanel.camera_angle.toUpperCase()}</span>
                        {selectedPanel.camera_movement && (
                          <span className="panel-badge text-amber">🎥 {selectedPanel.camera_movement.replace(/_/g, ' ').toUpperCase()}</span>
                        )}
                        {selectedPanel.focal_depth_plane && (
                          <span className="panel-badge">Depth: {selectedPanel.focal_depth_plane.replace(/_/g, ' ').toUpperCase()}</span>
                        )}
                        {selectedPanel.lighting_profile_id && (
                          <span className="panel-badge">Light: {selectedPanel.lighting_profile_id.replace(/_/g, ' ').toUpperCase()}</span>
                        )}
                        <span className="panel-badge">{selectedPanel.lens_feel}</span>
                      </div>
                      <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '6px' }}>
                        <strong>Composition:</strong> {selectedPanel.composition}
                      </div>
                      {selectedPanel.transition_type && (
                        <div style={{ fontSize: '12px', color: '#f59e0b', marginTop: '6px' }}>
                          <strong>Transition:</strong> {selectedPanel.transition_type.replace(/_/g, ' ').toUpperCase()}
                          {selectedPanel.visual_link && (
                            <span style={{ color: '#cbd5e1' }}> (Visual Link: <em>{selectedPanel.visual_link}</em>)</span>
                          )}
                        </div>
                      )}
                      {selectedPanel.subtext_context && (
                        <div style={{ fontSize: '12px', color: '#38bdf8', marginTop: '4px' }}>
                          <strong>Subtext Context:</strong> {selectedPanel.subtext_context}
                        </div>
                      )}
                    </div>

                    <div>
                      <div className="pane-kicker">ACTION &amp; CAPTION</div>
                      <div style={{ fontSize: '13px', color: '#f8fafc', marginTop: '4px' }}>
                        {selectedPanel.action_description || selectedPanel.action}
                      </div>
                      {selectedPanel.dialogue_excerpt && (
                        <div className="panel-dialogue-excerpt" style={{ marginTop: '8px' }}>
                          "{selectedPanel.dialogue_excerpt}"
                        </div>
                      )}
                    </div>

                    <div>
                      <div className="pane-kicker">CONTINUITY SPECIFICATIONS</div>
                      <div style={{ fontSize: '12px', color: '#cbd5e1', marginTop: '4px' }}>
                        {selectedPanel.continuity_notes || 'Preserves wardrobe, props, and lighting palette.'}
                      </div>
                      <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        {selectedPanel.characters_present && selectedPanel.characters_present.length > 0 && (
                          <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                            <strong style={{ color: '#cbd5e1' }}>Characters Present:</strong>{' '}
                            {selectedPanel.characters_present.join(', ')}
                          </div>
                        )}
                        {selectedPanel.objects_in_frame && selectedPanel.objects_in_frame.length > 0 && (
                          <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                            <strong style={{ color: '#cbd5e1' }}>Props in Frame (Canonical):</strong>{' '}
                            {selectedPanel.objects_in_frame.map((objId) => (
                              <span key={objId} className="panel-badge text-amber" style={{ marginRight: '4px', fontSize: '10px' }}>
                                {objId}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    <div>
                      <div className="pane-kicker">COMPILED MULTI-LAYER PROMPT</div>
                      <div className="panel-prompt-mono" style={{ maxHeight: '180px', overflowY: 'auto' }}>
                        {selectedPanel.compiled_prompt || selectedPanel.image_prompt || selectedPanel.visual_prompt}
                      </div>
                    </div>

                    {selectedPanel.negative_prompt && (
                      <div>
                        <div className="pane-kicker">NEGATIVE CONSTRAINTS</div>
                        <div style={{ fontSize: '11px', color: '#94a3b8', fontFamily: 'var(--font-mono)' }}>
                          {selectedPanel.negative_prompt}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
