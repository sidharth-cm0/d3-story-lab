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
  generateStoryboard,
  regeneratePanelVersion,
  selectPanelVersion,
  regeneratePage,
  externalRenderPanel,
  externalRenderPage,
  fetchCapabilities,
  runStoryboardSmokeTest,
} from '../api';
import { formatDisplayValue, safeExtractSvg } from '../utils/format';
import { VisualQaView } from './VisualQaView';

interface StoryboardViewerProps {
  project: ProjectData;
  loading?: boolean;
}

type SubTab = 'comic' | 'grid' | 'presentation' | 'visual_qa' | 'bible' | 'continuity';


export const StoryboardViewer: React.FC<StoryboardViewerProps> = ({ project }) => {
  const [storyboardData, setStoryboardData] = useState<StoryboardResponse | null>(null);
  const [visualBible, setVisualBible] = useState<VisualBible | null>(null);
  const [activeTab, setActiveTab] = useState<SubTab>('grid');
  const [activePage, setActivePage] = useState<number>(1);
  const [presentationIndex, setPresentationIndex] = useState<number>(0);
  const [densityMode, setDensityMode] = useState<string>('standard');
  const [selectedPanel, setSelectedPanel] = useState<StoryboardPanel | null>(null);
  const [showInspectorPrevis, setShowInspectorPrevis] = useState<boolean>(false);

  // Budget & On-Demand Provider selection
  const [selectedProvider, setSelectedProvider] = useState<'on_demand' | 'comfyui'>('on_demand');
  const [keyframeBudget, setKeyframeBudget] = useState<number>(8);
  const [showConfirmModal, setShowConfirmModal] = useState<boolean>(false);
  const [isGeneratingBatch, setIsGeneratingBatch] = useState<boolean>(false);

  const [fetching, setFetching] = useState(false);
  const [regeneratingPanelId, setRegeneratingPanelId] = useState<string | null>(null);
  const [regeneratingPage, setRegeneratingPage] = useState(false);
  const [renderingExternalPanelId, setRenderingExternalPanelId] = useState<string | null>(null);
  const [renderingExternalPage, setRenderingExternalPage] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Previs toggles, advanced drawer, and smoke test states
  const [showPrevisForPanel, setShowPrevisForPanel] = useState<Record<string, boolean>>({});
  const [showAdvanced, setShowAdvanced] = useState<boolean>(false);
  const [smokeTestResult, setSmokeTestResult] = useState<any>(null);
  const [isSmokeTesting, setIsSmokeTesting] = useState<boolean>(false);

  const handleRunSmokeTest = async () => {
    setIsSmokeTesting(true);
    setSmokeTestResult(null);
    try {
      const res = await runStoryboardSmokeTest();
      setSmokeTestResult(res);
    } catch (err: any) {
      setSmokeTestResult({ success: false, message: err.message || 'Smoke test failed' });
    } finally {
      setIsSmokeTesting(false);
    }
  };


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

  const [capabilities, setCapabilities] = useState<any>(null);
  const loadCapabilities = () => {
    fetchCapabilities()
      .then((caps) => setCapabilities(caps))
      .catch(() => {});
  };

  useEffect(() => {
    loadCapabilities();
  }, []);


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

  const handleGenerateSelectedKeyframes = async () => {
    setShowConfirmModal(false);
    setIsGeneratingBatch(true);
    setError(null);
    try {
      const data = await generateStoryboard(
        project.metadata.id,
        selectedProvider,
        'KEYFRAMES',
        keyframeBudget
      );
      setStoryboardData(data);
      const hasQuotaError = data.shot_plan?.panels?.some(
        (p) => p.fallback_reason === 'QUOTA_UNAVAILABLE' || p.status_message?.includes('quota')
      );
      if (hasQuotaError) {
        setError('Image generation quota unavailable.');
      }
    } catch (err: any) {
      setError(err.message || 'Image generation quota unavailable.');
    } finally {
      setIsGeneratingBatch(false);
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

  const renderArtworkFrame = (
    panel: StoryboardPanel,
    renderData: any,
    shotNum: number,
    isPresentation: boolean = false
  ) => {
    const imageUrl =
      panel.image_url ||
      panel.rendered_image_url ||
      (typeof renderData === 'object' ? renderData?.image_url : null);
    const hasRasterImage = Boolean(imageUrl && !imageUrl.endsWith('.svg'));
    const svgContent =
      panel.previs_svg ||
      panel.control_bundle?.previs_svg ||
      safeExtractSvg(renderData) ||
      panel.rendered_svg ||
      '';
    const isRegenerating = regeneratingPanelId === panel.id;
    const isGenerating = isRegenerating || (isGeneratingBatch && panel.status === 'GENERATING');
    const isFailed = panel.status === 'FAILED' || Boolean(panel.fallback_reason && !hasRasterImage && panel.fallback_reason !== 'OPEN_MODEL_NOT_CONNECTED');
    const showPrevis = showPrevisForPanel[panel.id];

    if (isGenerating) {
      return (
        <div className="storyboard-generating-shimmer" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: isPresentation ? '360px' : '200px', background: '#0a0d14', color: '#38bdf8', padding: '24px', textAlign: 'center' }}>
          <div style={{ fontSize: '32px', marginBottom: '8px' }}>⏳</div>
          <div style={{ fontWeight: 700, fontSize: '13px', letterSpacing: '0.05em', color: '#38bdf8' }}>GENERATING STILL FRAME...</div>
          <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>On-demand neural diffusion</div>
        </div>
      );
    }

    // Priority 1: Real raster artwork (ALWAYS takes precedence. Previs NEVER replaces final raster artwork.)
    if (hasRasterImage) {
      return (
        <img
          src={imageUrl!}
          alt={panel.caption || `Shot ${shotNum}`}
          className="comic-panel-artwork"
          loading="lazy"
        />
      );
    }

    // Priority 2: Failed state with provider error & retry
    if (isFailed) {
      const errorMsg = panel.error_message || panel.status_message || (
        panel.fallback_reason === 'QUOTA_UNAVAILABLE'
          ? 'Image generation quota unavailable.'
          : panel.fallback_reason === 'MODEL_UNAVAILABLE'
          ? 'Configured model is unavailable through this provider.'
          : panel.fallback_reason === 'AUTH_FAILED'
          ? 'Authentication failed. Please verify HF_TOKEN.'
          : 'Generation failed or timed out.'
      );

      return (
        <div className="storyboard-error-frame" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: isPresentation ? '360px' : '200px', background: '#181012', border: '1px dashed #ef4444', padding: '16px', textAlign: 'center' }}>
          <div style={{ fontSize: '24px', marginBottom: '4px' }}>⚠️</div>
          <div style={{ color: '#fca5a5', fontWeight: 700, fontSize: '12px', marginBottom: '4px' }}>
            {panel.fallback_reason || 'GENERATION FAILED'}
          </div>
          <div style={{ color: '#94a3b8', fontSize: '11px', marginBottom: '12px', maxWidth: '280px', lineHeight: 1.4 }}>
            {errorMsg}
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              type="button"
              className="btn-cinematic-secondary"
              style={{ fontSize: '11px', padding: '4px 10px', borderColor: '#ef4444', color: '#fca5a5' }}
              onClick={(e) => {
                e.stopPropagation();
                handleRegenerateSinglePanel(panel.id);
              }}
              disabled={isRegenerating}
            >
              ↻ Retry Generation
            </button>
            {svgContent && (
              <button
                type="button"
                className="btn-cinematic-secondary"
                style={{ fontSize: '11px', padding: '4px 10px', borderColor: '#38bdf8', color: '#38bdf8' }}
                onClick={(e) => {
                  e.stopPropagation();
                  setShowPrevisForPanel(prev => ({ ...prev, [panel.id]: !prev[panel.id] }));
                }}
              >
                {showPrevis ? 'Hide Guide' : '📐 View Previs Guide'}
              </button>
            )}
          </div>
          {showPrevis && svgContent && (
            <div style={{ marginTop: '12px', width: '100%', borderTop: '1px solid #334155', paddingTop: '8px' }} dangerouslySetInnerHTML={{ __html: svgContent }} />
          )}
        </div>
      );
    }

    // Priority 3: Previs guide available (structural composition sketch)
    if (svgContent) {
      return (
        <div className="storyboard-previs-container" style={{ position: 'relative', width: '100%', height: '100%', minHeight: isPresentation ? '360px' : '200px' }}>
          <div
            className={isPresentation ? 'storyboard-svg-wrapper' : 'comic-svg-art'}
            dangerouslySetInnerHTML={{ __html: svgContent }}
          />
          <div style={{ position: 'absolute', top: '8px', right: '8px', zIndex: 10 }}>
            <button
              type="button"
              className="btn-cinematic"
              style={{ fontSize: '11px', padding: '4px 10px', background: '#0284c7', borderColor: '#38bdf8', color: '#fff', boxShadow: '0 2px 6px rgba(0,0,0,0.5)', cursor: 'pointer' }}
              onClick={(e) => {
                e.stopPropagation();
                handleRegenerateSinglePanel(panel.id);
              }}
              disabled={isRegenerating}
              title="Generate on-demand neural still frame for this shot"
            >
              ★ Generate Shot
            </button>
          </div>
        </div>
      );
    }

    // Priority 4: Clean ungenerated state
    return (
      <div className="storyboard-unrendered-clean" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: isPresentation ? '360px' : '200px', background: '#0a0d14', border: '1px dashed #334155', padding: '20px', textAlign: 'center' }}>
        <div style={{ fontSize: '32px', marginBottom: '8px' }}>🎬</div>
        <div style={{ color: '#f8fafc', fontWeight: 600, fontSize: '13px', marginBottom: '4px' }}>
          {(panel.shot_type || 'SHOT').toUpperCase()} • {(panel.camera_angle || 'EYE LEVEL').toUpperCase()}
        </div>
        <div style={{ color: '#64748b', fontSize: '11px', marginBottom: '14px', maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {panel.action || panel.action_description || 'Scene unfolds'}
        </div>
        <button
          type="button"
          className="btn-cinematic"
          style={{ fontSize: '11px', padding: '5px 12px', background: '#0284c7', borderColor: '#38bdf8', color: '#fff', cursor: 'pointer' }}
          onClick={(e) => {
            e.stopPropagation();
            handleRegenerateSinglePanel(panel.id);
          }}
          disabled={isRegenerating}
        >
          ★ Generate Shot
        </button>
      </div>
    );
  };

  return (
    <div className="cinematic-storyboard-pane">
      {/* Top Header Controls */}
      <div className="pane-header">
        <div>
          <span className="pane-kicker">CINEMATIC PREPARATION &amp; GRAPHIC NOVEL BOARDS</span>
          <h2 className="pane-title">STORYBOARD</h2>
        </div>

        <div className="pane-actions" style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Primary Action 1: Plan / Re-Plan */}
          <button
            className="btn-cinematic-primary"
            onClick={handlePlanStoryboard}
            disabled={fetching || isGeneratingBatch}
            data-testid="btn-plan-storyboard"
          >
            {fetching ? 'PLANNING FRAMES...' : panels.length > 0 ? '↻ RE-PLAN SHOTS' : 'PREPARE SHOT PLAN'}
          </button>

          {/* Primary Action 2: Generate Storyboard Keyframes */}
          {panels.length > 0 && (
            <button
              className="btn-cinematic-primary"
              onClick={() => setShowConfirmModal(true)}
              disabled={isGeneratingBatch || fetching}
              title="Generate selected still storyboard images. Free/limited provider availability depends on current quota."
              data-testid="btn-generate-selected-frames"
              style={{ background: '#0284c7', borderColor: '#38bdf8' }}
            >
              {isGeneratingBatch ? 'GENERATING FRAMES...' : 'GENERATE SELECTED STORYBOARD FRAMES'}
            </button>
          )}

          {/* Keyframe Generation Budget */}
          <div className="density-selector" title="Keyframe generation budget">
            <span>BUDGET:</span>
            <select
              value={keyframeBudget}
              onChange={(e) => setKeyframeBudget(Number(e.target.value))}
              disabled={fetching || isGeneratingBatch}
              data-testid="select-keyframe-budget"
            >
              <option value={4}>KEYFRAMES 4</option>
              <option value={8}>KEYFRAMES 8</option>
              <option value={12}>KEYFRAMES 12</option>
            </select>
          </div>

          {/* Provider Selection */}
          <div className="density-selector" title="Free/limited provider availability depends on current quota.">
            <span>PROVIDER:</span>
            <select
              value={selectedProvider}
              onChange={(e) => setSelectedProvider(e.target.value as 'on_demand' | 'comfyui')}
              disabled={fetching || isGeneratingBatch}
              data-testid="select-storyboard-provider"
            >
              <option value="on_demand">ON-DEMAND</option>
              <option value="comfyui">COMFYUI</option>
            </select>
            {selectedProvider === 'on_demand' && (
              <span className="quota-disclaimer-badge" style={{ fontSize: '0.7rem', color: '#f59e0b', marginLeft: '6px' }}>
                Free/limited provider availability depends on current quota.
              </span>
            )}
          </div>

          {/* Advanced Controls Toggle */}
          <button
            type="button"
            className={`btn-cinematic-secondary ${showAdvanced ? 'active' : ''}`}
            onClick={() => setShowAdvanced((prev) => !prev)}
            title="Toggle advanced options: density, diagnostic smoke test, and page-by-page renders"
          >
            {showAdvanced ? '▲ OPTIONS' : '⚙ ADVANCED'}
          </button>
        </div>
      </div>

      {/* Advanced Inspector & Diagnostics Drawer */}
      {showAdvanced && (
        <div
          className="advanced-options-drawer"
          style={{
            background: '#090d16',
            border: '1px solid #1e293b',
            padding: '10px 16px',
            borderRadius: '8px',
            margin: '8px 0 12px 0',
            display: 'flex',
            gap: '12px',
            alignItems: 'center',
            flexWrap: 'wrap',
            fontSize: '0.85rem',
          }}
        >
          <div className="density-selector" title="Shot coverage density per scene">
            <span>DENSITY:</span>
            <select
              value={densityMode}
              onChange={(e) => setDensityMode(e.target.value)}
              disabled={fetching || regeneratingPage || renderingExternalPage || isGeneratingBatch}
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
                disabled={regeneratingPage || fetching || isGeneratingBatch}
                title={`Regenerate all visual frames on Page ${activePage}`}
              >
                {regeneratingPage ? 'REGENERATING PAGE...' : `↻ REGENERATE PAGE ${activePage}`}
              </button>

              <button
                className="btn-cinematic-secondary"
                onClick={() => handleExternalRenderPage(activePage)}
                disabled={renderingExternalPage || fetching || isGeneratingBatch}
                title="Render panels using configured open-model generation runtime"
              >
                {renderingExternalPage ? 'RENDERING OPEN-MODEL...' : `⚡ RENDER PAGE (OPEN-MODEL)`}
              </button>
            </>
          )}

          <button
            type="button"
            className="btn-cinematic-secondary"
            onClick={handleRunSmokeTest}
            disabled={isSmokeTesting}
            title="Execute backend single-request smoke test to verify live image provider without faking"
          >
            {isSmokeTesting ? 'RUNNING SMOKE TEST...' : '🧪 RUN SMOKE TEST'}
          </button>

          {capabilities && (
            <span style={{ fontSize: '0.75rem', color: capabilities.available ? '#34d399' : '#f59e0b', marginLeft: 'auto' }}>
              ● {capabilities.provider?.toUpperCase()} • {capabilities.status || 'READY'} ({capabilities.model_generation_capability || capabilities.model})
            </span>
          )}
        </div>
      )}

      {/* Smoke Test Feedback Box */}
      {smokeTestResult && (
        <div
          style={{
            background: smokeTestResult.success ? '#064e3b' : '#450a0a',
            border: `1px solid ${smokeTestResult.success ? '#059669' : '#b91c1c'}`,
            borderRadius: '6px',
            padding: '8px 12px',
            margin: '8px 0',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '0.8rem',
            color: smokeTestResult.success ? '#a7f3d0' : '#fecaca',
          }}
        >
          <div>
            <strong>Smoke Test Result:</strong> {smokeTestResult.message}
            {smokeTestResult.file_path && ` (Saved: ${smokeTestResult.file_path})`}
          </div>
          <button
            type="button"
            style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer', fontWeight: 'bold' }}
            onClick={() => setSmokeTestResult(null)}
          >
            ✕
          </button>
        </div>
      )}

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div
          className="modal-backdrop"
          data-testid="generate-confirm-modal"
          onClick={() => setShowConfirmModal(false)}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
          }}
        >
          <div
            className="modal-container"
            onClick={(e) => e.stopPropagation()}
            style={{
              background: '#0f172a',
              border: '1px solid #334155',
              borderRadius: '8px',
              padding: '1.5rem',
              maxWidth: '500px',
              width: '90%',
              color: '#f8fafc',
            }}
          >
            <h3 style={{ margin: '0 0 0.75rem 0', fontSize: '1.15rem' }}>
              Confirm Storyboard Generation
            </h3>
            <p style={{ margin: '0 0 0.75rem 0', color: '#38bdf8', fontWeight: 600, fontSize: '1rem' }}>
              {keyframeBudget} storyboard images will be generated.
            </p>
            <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.85rem', color: '#94a3b8' }}>
              <strong>Selected Provider:</strong> {selectedProvider === 'on_demand' ? 'ON-DEMAND' : 'COMFYUI'}
            </p>
            <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.8rem', color: '#f59e0b' }}>
              Free/limited provider availability depends on current quota.
            </p>
            <p style={{ margin: '0 0 1.25rem 0', fontSize: '0.75rem', color: '#64748b' }}>
              Generates still storyboard images (PNG/JPEG/WebP) directly persisted to project storage. D3 Story Lab does NOT generate video or animations.
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button
                type="button"
                className="btn-cinematic-secondary"
                onClick={() => setShowConfirmModal(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-cinematic-primary"
                onClick={handleGenerateSelectedKeyframes}
                data-testid="btn-confirm-generate-batch"
              >
                Confirm &amp; Generate
              </button>
            </div>
          </div>
        </div>
      )}


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
          <button
            className={`subtab-btn ${activeTab === 'visual_qa' ? 'active' : ''}`}
            onClick={() => setActiveTab('visual_qa')}
            data-testid="subtab-visual-qa"
          >
            🔍 VISUAL QA
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

            <button
              className="btn-cinematic-secondary"
              style={{ fontSize: '11px', padding: '4px 10px', marginLeft: 'auto' }}
              onClick={() => handleRegeneratePage(activePage)}
              disabled={regeneratingPage}
              title={`Regenerate visual panels on Page ${activePage}`}
            >
              {regeneratingPage ? '↻...' : `↻ REGENERATE PAGE ${activePage}`}
            </button>
          </div>
        )}
      </div>

      {capabilities && !capabilities.available && (
        <div
          className="runtime-unconnected-banner"
          data-testid="runtime-unconnected-banner"
          style={{
            background: '#451a03',
            border: '1px solid #d97706',
            color: '#fef3c7',
            padding: '0.6rem 1rem',
            borderRadius: '6px',
            margin: '8px 0',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '0.85rem',
          }}
        >
          <div>
            <strong>Open-model storyboard runtime not connected.</strong> Previs guide available.
          </div>
          <button
            type="button"
            className="subtab-btn"
            onClick={() => setActiveTab('visual_qa')}
            style={{
              fontSize: '0.75rem',
              padding: '0.25rem 0.5rem',
              background: '#78350f',
              border: '1px solid #d97706',
              color: '#fff',
              cursor: 'pointer',
              borderRadius: '4px',
            }}
          >
            Open Visual QA
          </button>
        </div>
      )}

      {error && (
        <div className="modal-error-box" style={{ margin: '12px 0' }}>
          {error}
        </div>
      )}


      {/* Main Content Area */}
      <div className="storyboard-content-scroll">
        {panels.length === 0 ? (
          <div style={{ maxWidth: '640px', margin: '60px auto', textAlign: 'center', padding: '36px 24px', background: '#0a0d14', border: '1px solid #1e293b', borderRadius: '8px' }}>
            <div style={{ fontSize: '42px', marginBottom: '16px' }}>🎬</div>
            <h3 style={{ color: '#f8fafc', fontSize: '18px', margin: '0 0 8px 0', letterSpacing: '0.02em' }}>
              {project.screenplay ? 'Screenplay Ready for Cinematic Planning' : 'Screenplay Required First'}
            </h3>
            <p style={{ color: '#94a3b8', fontSize: '13px', lineHeight: 1.5, margin: '0 0 24px 0' }}>
              {project.screenplay
                ? 'Prepare an 8–12 beat keyframe shot plan with visual continuity tracking, composition previs guides, and on-demand neural still frames.'
                : 'Generate a screenplay under the SCRIPT tab first, then return here to plan cinematic frames and generate storyboard images.'}
            </p>
            {project.screenplay && (
              <button
                type="button"
                className="btn-cinematic"
                onClick={handlePlanStoryboard}
                disabled={fetching}
                style={{ fontSize: '13px', padding: '10px 24px', background: '#0284c7', borderColor: '#38bdf8', color: '#fff', cursor: 'pointer' }}
              >
                {fetching ? 'PREPARING SHOT PLAN...' : '🎬 PREPARE SHOT PLAN'}
              </button>
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

                      const imageUrl =
                        panel.image_url ||
                        panel.rendered_image_url ||
                        (typeof renderData === 'object' ? renderData?.image_url : null);
                      const hasRaster = Boolean(imageUrl && !imageUrl.endsWith('.svg'));
                      const isRegenerating = regeneratingPanelId === panel.id;
                      const isFailed = panel.status === 'FAILED' || Boolean(panel.fallback_reason && !hasRaster && panel.fallback_reason !== 'OPEN_MODEL_NOT_CONNECTED');
                      const badgeLabel = isRegenerating
                        ? 'GENERATING...'
                        : hasRaster
                        ? 'READY (STILL IMAGE)'
                        : isFailed
                        ? (panel.fallback_reason || 'FAILED')
                        : svgContent
                        ? 'PREVIS GUIDE'
                        : 'UNGENERATED';
                      const badgeClass = isRegenerating
                        ? 'badge-generating'
                        : hasRaster
                        ? 'badge-ai-image'
                        : isFailed
                        ? 'badge-failed'
                        : svgContent
                        ? 'badge-previs-guide'
                        : 'badge-unrendered';

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
                              {!hasRaster && panel.fallback_reason && (
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
                            {renderArtworkFrame(panel, renderData, shotNum)}

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

                  const imageUrl =
                    panel.image_url ||
                    panel.rendered_image_url ||
                    (typeof renderData === 'object' ? renderData?.image_url : null);
                  const hasRaster = Boolean(imageUrl && !imageUrl.endsWith('.svg'));
                  const isRegenerating = regeneratingPanelId === panel.id;
                  const isFailed = panel.status === 'FAILED' || Boolean(panel.fallback_reason && !hasRaster && panel.fallback_reason !== 'OPEN_MODEL_NOT_CONNECTED');
                  const badgeLabel = isRegenerating
                    ? 'GENERATING...'
                    : hasRaster
                    ? 'READY (STILL IMAGE)'
                    : isFailed
                    ? (panel.fallback_reason || 'FAILED')
                    : svgContent
                    ? 'PREVIS GUIDE'
                    : 'UNGENERATED';
                  const badgeClass = isRegenerating
                    ? 'badge-generating'
                    : hasRaster
                    ? 'badge-ai-image'
                    : isFailed
                    ? 'badge-failed'
                    : svgContent
                    ? 'badge-previs-guide'
                    : 'badge-unrendered';

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
                          {!hasRaster && panel.fallback_reason && (
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
                        {renderArtworkFrame(panel, renderData, shotNum)}
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
                  const shotNum = panel.shot_number ?? panel.panel_number ?? currentIdx + 1;
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
                        {renderArtworkFrame(panel, renderData, shotNum, true)}
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

            {/* 5. VISUAL QA KEYFRAMES VIEW */}
            {activeTab === 'visual_qa' && (
              <VisualQaView
                panels={panels}
                projectId={project.metadata?.id}
                capabilities={capabilities}
                onRefreshCapabilities={loadCapabilities}
              />
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
                  ) : showInspectorPrevis && (selectedPanel.previs_svg || selectedPanel.rendered_svg) ? (
                    <div className="storyboard-svg-wrapper">
                      <div style={{ position: 'absolute', top: 8, left: 8, zIndex: 10, background: 'rgba(2, 132, 199, 0.9)', color: '#fff', fontSize: '10px', padding: '3px 8px', borderRadius: '4px', fontWeight: 700 }}>
                        PREVIS GUIDE (STRUCTURAL COMPOSITION)
                      </div>
                      <div dangerouslySetInnerHTML={{ __html: selectedPanel.previs_svg || selectedPanel.rendered_svg || '' }} />
                    </div>
                  ) : (
                    <div className="shot-unrendered-container" style={{ padding: '32px 16px', textAlign: 'center', background: '#0a0f1d', borderRadius: '4px', border: '1px dashed #334155' }}>
                      <div style={{ fontSize: '24px', marginBottom: '8px' }}>🎨</div>
                      <div style={{ color: '#f8fafc', fontWeight: 600, fontSize: '13px', marginBottom: '4px' }}>
                        Storyboard render unavailable
                      </div>
                      <div style={{ color: '#94a3b8', fontSize: '11px', marginBottom: '14px', maxWidth: '300px', margin: '0 auto 14px' }}>
                        Open-model renderer not configured or shot is unrendered keyframe. Procedural SVG is retained only as an internal previs guide.
                      </div>
                      {(selectedPanel.previs_svg || selectedPanel.rendered_svg) && (
                        <button
                          type="button"
                          className="btn-cinematic-secondary"
                          style={{ fontSize: '11px', padding: '5px 10px', borderColor: '#38bdf8', color: '#38bdf8' }}
                          onClick={() => setShowInspectorPrevis(!showInspectorPrevis)}
                        >
                          {showInspectorPrevis ? '✕ Hide Previs Guide' : '📐 Previs guide available (Inspect)'}
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {/* Previs toggle if raster image is active */}
                {selectedPanel.image_url && !selectedPanel.image_url.endsWith('.svg') && (selectedPanel.previs_svg || selectedPanel.rendered_svg) && (
                  <div style={{ marginTop: '8px', display: 'flex', justifyContent: 'flex-end' }}>
                    <button
                      type="button"
                      className="btn-cinematic-secondary"
                      style={{ fontSize: '10px', padding: '4px 8px' }}
                      onClick={() => setShowInspectorPrevis(!showInspectorPrevis)}
                    >
                      {showInspectorPrevis ? 'Hide Previs Overlay' : 'View Previs & Composition Guide'}
                    </button>
                  </div>
                )}
                {showInspectorPrevis && selectedPanel.image_url && !selectedPanel.image_url.endsWith('.svg') && (selectedPanel.previs_svg || selectedPanel.rendered_svg) && (
                  <div style={{ marginTop: '8px', border: '1px solid #38bdf8', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ background: '#0c4a6e', color: '#7dd3fc', fontSize: '10px', padding: '4px 8px', fontWeight: 700 }}>
                      PREVIS GUIDE (STRUCTURAL COMPOSITION & POSE)
                    </div>
                    <div
                      className="storyboard-svg-wrapper"
                      dangerouslySetInnerHTML={{ __html: selectedPanel.previs_svg || selectedPanel.rendered_svg || '' }}
                    />
                  </div>
                )}

                <div style={{ marginTop: '16px' }}>
                  <div className="pane-kicker" style={{ marginBottom: '8px' }}>
                    GENERATION VERSIONS ({selectedPanel.versions?.length || 1})
                  </div>
                  <div style={{ display: 'flex', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
                    <button
                      className="btn-cinematic-secondary"
                      onClick={() => handleRegenerateSinglePanel(selectedPanel.id)}
                      disabled={regeneratingPanelId === selectedPanel.id}
                      title="Regenerate panel artwork with active provider"
                      style={{ padding: '6px 12px', fontSize: '11px' }}
                    >
                      {regeneratingPanelId === selectedPanel.id ? 'REGENERATING...' : '↻ REGENERATE ARTWORK'}
                    </button>
                    <button
                      className="btn-cinematic-secondary"
                      onClick={() => handleExternalRenderPanel(selectedPanel.id)}
                      disabled={renderingExternalPanelId === selectedPanel.id}
                      title="Render with open-model or external runtime"
                      style={{ padding: '6px 12px', fontSize: '11px', borderColor: '#7c3aed', color: '#c4b5fd' }}
                    >
                      {renderingExternalPanelId === selectedPanel.id ? 'RENDERING EXTERNALLY...' : '⚡ RENDER WITH RUNTIME'}
                    </button>
                  </div>
                  <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: '10px', fontStyle: 'italic' }}>
                    Open-model runtime / external render. Availability and endpoints depend on configuration.
                  </div>
                  <div className="inspector-versions-list">
                    {(selectedPanel.versions && selectedPanel.versions.length > 0
                      ? selectedPanel.versions
                      : [
                          {
                            version: 1,
                            image_url: selectedPanel.image_url || '',
                            provider: selectedPanel.provider || 'open_model_storyboard',
                            mode: (selectedPanel as any).mode || 'open_model',
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
                        <div style={{ fontSize: '9px', color: ver.mode === 'ai_image' || ver.mode === 'open_model' ? '#a78bfa' : (ver.mode === 'hand_drawn' || ver.mode === 'previs' ? '#38bdf8' : '#f59e0b') }}>
                          {ver.mode === 'ai_image' || ver.mode === 'open_model' ? 'OPEN-MODEL' : (ver.mode === 'hand_drawn' || ver.mode === 'previs' ? 'PREVIS GUIDE' : 'FALLBACK')}
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

                const isAiMode = currentVersion?.mode === 'ai_image' || currentVersion?.mode === 'open_model' || (selectedPanel as any).mode === 'ai_image' || (selectedPanel as any).mode === 'open_model';
                const isHandDrawnMode =
                  !isAiMode &&
                  (currentVersion?.mode === 'hand_drawn' ||
                    currentVersion?.mode === 'previs' ||
                    currentVersion?.provider === 'hand_drawn_storyboard' ||
                    selectedPanel.provider === 'hand_drawn_storyboard' ||
                    (selectedPanel as any).mode === 'hand_drawn' ||
                    !currentVersion?.fallback_reason);

                const currentReason = isHandDrawnMode ? null : (currentVersion?.fallback_reason || selectedPanel.fallback_reason);
                const currentContinuity = currentVersion?.continuity_mode || selectedPanel.continuity_mode || 'Deterministic Visual Bible';
                const currentProvider = isAiMode
                  ? (currentVersion?.provider || selectedPanel.provider || 'OpenModelStoryboardProvider')
                  : ((currentVersion?.render_metadata?.renderer as string) || (currentVersion?.provider === 'hand_drawn_storyboard' ? 'HandDrawnStoryboardProvider' : currentVersion?.provider) || selectedPanel.provider || 'PrevisControlRenderer');
                const currentStyle = (currentVersion?.render_metadata?.style as string) || 'Cinematic Film Still';

                return (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    {/* 1. NARRATIVE & STAGING LAYER */}
                    <div className="inspector-narrative-section">
                      <div className="pane-kicker">NARRATIVE &amp; STAGING</div>
                      <div style={{ fontSize: '13px', color: '#f8fafc', marginTop: '6px', lineHeight: 1.5 }}>
                        {selectedPanel.action_description || selectedPanel.action}
                      </div>

                      {selectedPanel.dialogue_excerpt && (
                        <div className="panel-dialogue-excerpt" style={{ marginTop: '8px' }}>
                          "{selectedPanel.dialogue_excerpt}"
                        </div>
                      )}

                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: '8px', flexWrap: 'wrap' }}>
                        <span className="panel-location-tag">
                          📍 {formatDisplayValue(selectedPanel.location_name || project.world?.locations?.[selectedPanel.location_id]?.name || selectedPanel.location_id || 'Unknown Location')}
                        </span>
                        {selectedPanel.subtext_context && (
                          <span style={{ fontSize: '11px', color: '#38bdf8' }}>
                            Subtext: <em>{selectedPanel.subtext_context}</em>
                          </span>
                        )}
                      </div>

                      {((selectedPanel.character_names && selectedPanel.character_names.length > 0) || (selectedPanel.characters_present && selectedPanel.characters_present.length > 0)) && (
                        <div style={{ marginTop: '8px', display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' }}>
                          <span style={{ fontSize: '11px', color: '#94a3b8' }}>CHARACTERS:</span>
                          {(selectedPanel.character_names || selectedPanel.characters_present || []).map((c: string) => (
                            <span key={c} className="char-chip">👤 {formatDisplayValue(project.world?.characters?.[c]?.name || c)}</span>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* 2. CINEMATIC TECHNICAL SPECS */}
                    <div className="inspector-cinematic-section">
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
                    </div>

                    {/* 3. TECHNICAL INFRASTRUCTURE & METADATA (Collapsible) */}
                    <details className="inspector-technical-details" open={false}>
                      <summary className="inspector-technical-summary">
                        ⚙ TECHNICAL INFRASTRUCTURE &amp; METADATA
                      </summary>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '10px' }}>
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
                                SOURCE: {isAiMode ? 'OPEN-MODEL STORYBOARD' : isHandDrawnMode ? 'PREVIS GUIDE' : 'FALLBACK COMIC'}
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
                              <span style={{ color: '#94a3b8' }}>PREVIS ENGINE:</span>
                              <span style={{ color: '#38bdf8', fontSize: '11px', fontWeight: 600 }}>
                                Deterministic Procedural Previs (Internal Only)
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
                              ⚠ Image generation unavailable because quota is exceeded or runtime is unreachable.
                            </div>
                          )}
                        </div>

                        {/* Control Guides & Previs Bundle */}
                        {selectedPanel.control_bundle && (
                          <div>
                            <div className="pane-kicker">CONTROL GUIDES &amp; PREVIS BUNDLE</div>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))', gap: '8px', marginTop: '6px' }}>
                              <div style={{ padding: '8px', background: '#0f172a', border: '1px solid #1e293b', borderRadius: '4px', fontSize: '11px' }}>
                                <div style={{ color: '#94a3b8', fontWeight: 600, marginBottom: '2px' }}>POSE GUIDE</div>
                                <div style={{ color: selectedPanel.control_bundle.pose_map ? '#38bdf8' : '#64748b', fontSize: '10px' }}>
                                  {selectedPanel.control_bundle.pose_map ? '✓ Available' : 'Pending'}
                                </div>
                              </div>
                              <div style={{ padding: '8px', background: '#0f172a', border: '1px solid #1e293b', borderRadius: '4px', fontSize: '11px' }}>
                                <div style={{ color: '#94a3b8', fontWeight: 600, marginBottom: '2px' }}>EDGE MAP</div>
                                <div style={{ color: selectedPanel.control_bundle.edge_map ? '#38bdf8' : '#64748b', fontSize: '10px' }}>
                                  {selectedPanel.control_bundle.edge_map ? '✓ Available' : 'Pending'}
                                </div>
                              </div>
                              <div style={{ padding: '8px', background: '#0f172a', border: '1px solid #1e293b', borderRadius: '4px', fontSize: '11px' }}>
                                <div style={{ color: '#94a3b8', fontWeight: 600, marginBottom: '2px' }}>DEPTH MAP</div>
                                <div style={{ color: selectedPanel.control_bundle.depth_map ? '#38bdf8' : '#64748b', fontSize: '10px' }}>
                                  {selectedPanel.control_bundle.depth_map ? '✓ Available' : 'Pending'}
                                </div>
                              </div>
                              <div style={{ padding: '8px', background: '#0f172a', border: '1px solid #1e293b', borderRadius: '4px', fontSize: '11px' }}>
                                <div style={{ color: '#94a3b8', fontWeight: 600, marginBottom: '2px' }}>COMPOSITION</div>
                                <div style={{ color: selectedPanel.control_bundle.composition_mask ? '#38bdf8' : '#64748b', fontSize: '10px' }}>
                                  {selectedPanel.control_bundle.composition_mask ? '✓ Masked' : 'Standard'}
                                </div>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Continuity Specs */}
                        <div>
                          <div className="pane-kicker">CONTINUITY SPECIFICATIONS</div>
                          <div style={{ fontSize: '12px', color: '#cbd5e1', marginTop: '4px' }}>
                            {selectedPanel.continuity_notes || 'Preserves wardrobe, props, and lighting palette.'}
                          </div>
                          {selectedPanel.objects_in_frame && selectedPanel.objects_in_frame.length > 0 && (
                            <div style={{ marginTop: '6px', fontSize: '11px', color: '#94a3b8' }}>
                              <strong style={{ color: '#cbd5e1' }}>Props in Frame (Canonical):</strong>{' '}
                              {selectedPanel.objects_in_frame.map((objId) => (
                                <span key={objId} className="panel-badge text-amber" style={{ marginRight: '4px', fontSize: '10px' }}>
                                  {objId}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Compiled Multi-Layer Prompt */}
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

                        {/* Raw Identifiers & Metadata */}
                        <div style={{ fontSize: '10px', color: '#64748b', fontFamily: 'var(--font-mono)', borderTop: '1px solid #1e293b', paddingTop: '8px' }}>
                          <div>PANEL ID: {selectedPanel.id}</div>
                          {selectedPanel.source_screenplay_block_ids && selectedPanel.source_screenplay_block_ids.length > 0 && (
                            <div>SOURCE BLOCKS: {selectedPanel.source_screenplay_block_ids.join(', ')}</div>
                          )}
                        </div>
                      </div>
                    </details>
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
