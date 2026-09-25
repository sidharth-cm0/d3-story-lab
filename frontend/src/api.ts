import {
  ProjectMetadata,
  ProjectData,
  Event,
  StoryboardResponse,
  StoryboardPanel,
  StoryOutline,
  StorySynopsis,
  ProviderStatusResponse,
  StructureDefinition,
  StoryBlueprint,
  CharacterArcReport,
  CausalContinuitySummary,
  CharacterProfileDraft,
  CharacterInput,
  CompletenessReport,
  FieldAuthority,
  CharacterDynamicsProfile,
} from './types';

const BASE_URL = '/api';

export async function fetchHealth(): Promise<{ status: string; provider: string; version: string }> {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error('Failed to fetch health');
  return res.json();
}

export async function fetchProjects(): Promise<ProjectMetadata[]> {
  const res = await fetch(`${BASE_URL}/projects`);
  if (!res.ok) throw new Error('Failed to fetch projects');
  return res.json();
}

export async function createProject(
  seed_prompt: string,
  title?: string,
  input_type: string = 'beginning',
  target_duration_minutes: number = 20,
  structure_mode: string = 'AUTO',
  structure_type?: string,
  secondary_structure?: string,
  presentation_strategy: string = 'CHRONOLOGICAL'
): Promise<ProjectMetadata> {
  const res = await fetch(`${BASE_URL}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      seed_prompt,
      title,
      input_type,
      target_duration_minutes,
      structure_mode,
      structure_type,
      secondary_structure,
      presentation_strategy,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to create project' }));
    throw new Error(err.detail || 'Failed to create project');
  }
  return res.json();
}

export async function fetchProject(projectId: string): Promise<ProjectData> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}`);
  if (!res.ok) throw new Error('Failed to fetch project');
  return res.json();
}

export async function deleteProject(projectId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete project');
}

export async function fetchOutline(projectId: string): Promise<StoryOutline> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/outline`);
  if (!res.ok) throw new Error('Failed to fetch story outline');
  return res.json();
}

export async function fetchSynopsis(projectId: string): Promise<StorySynopsis> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/synopsis`);
  if (!res.ok) throw new Error('Failed to fetch synopsis');
  return res.json();
}

export async function stepSimulation(projectId: string, ticks: number = 1): Promise<{ current_tick: number; new_events: Event[] }> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/step`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticks }),
  });
  if (!res.ok) throw new Error('Failed to step simulation');
  return res.json();
}

export async function runSimulation(projectId: string, num_ticks: number = 5): Promise<{ current_tick: number; total_new_events: number }> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ num_ticks }),
  });
  if (!res.ok) throw new Error('Failed to run simulation');
  return res.json();
}

export async function generateScreenplay(
  projectId: string,
  framingMode: string = 'chronological'
): Promise<{
  fountain_text: string;
  total_scenes: number;
  total_beats: number;
  total_panels?: number;
  screenplay_quality?: any;
  storyboard_quality?: any;
}> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/generate-screenplay`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ framing_mode: framingMode }),
  });
  if (!res.ok) throw new Error('Failed to generate screenplay');
  return res.json();
}

export function getDownloadUrl(projectId: string): string {
  return `${BASE_URL}/projects/${projectId}/screenplay/download`;
}

export function getExportUrl(projectId: string, format: string): string {
  return `${BASE_URL}/projects/${projectId}/export/${format}`;
}

export async function fetchStoryboard(projectId: string): Promise<StoryboardResponse> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/storyboard`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to fetch storyboard' }));
    throw new Error(err.detail || 'Failed to fetch storyboard');
  }
  return res.json();
}

export async function fetchVisualBible(projectId: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/visual-bible`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to fetch visual bible' }));
    throw new Error(err.detail || 'Failed to fetch visual bible');
  }
  return res.json();
}

export async function planStoryboard(
  projectId: string,
  densityMode: string = 'standard',
  panelsPerPage: number = 4,
  renderMode: string = 'KEYFRAMES',
): Promise<StoryboardResponse> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/storyboard/plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ density_mode: densityMode, panels_per_page: panelsPerPage, render_mode: renderMode }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to plan storyboard' }));
    throw new Error(err.detail || 'Failed to plan storyboard');
  }
  return res.json();
}

export async function generateStoryboard(
  projectId: string,
  provider?: string,
  renderMode: string = 'KEYFRAMES',
  keyframeBudget: number = 8,
): Promise<StoryboardResponse> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/storyboard/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider, render_mode: renderMode, keyframe_budget: keyframeBudget }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to generate storyboard' }));
    throw new Error(err.detail || 'Failed to generate storyboard');
  }
  return res.json();
}

export async function fetchCapabilities(): Promise<any> {
  const res = await fetch(`${BASE_URL}/storyboard/capabilities`);
  if (!res.ok) throw new Error('Failed to fetch storyboard capabilities');
  return res.json();
}

export async function runStoryboardSmokeTest(prompt?: string): Promise<any> {
  const url = prompt
    ? `${BASE_URL}/storyboard/smoke-test?prompt=${encodeURIComponent(prompt)}`
    : `${BASE_URL}/storyboard/smoke-test`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to run storyboard smoke test');
  return res.json();
}

export async function configureRenderer(
  provider: string,
  runtimeUrl?: string,
  model?: string,
  apiKey?: string,
): Promise<any> {
  const res = await fetch(`${BASE_URL}/storyboard/configure`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider, runtime_url: runtimeUrl, model, api_key: apiKey }),
  });
  if (!res.ok) throw new Error('Failed to configure storyboard renderer');
  return res.json();
}


export async function fetchControlBundle(projectId: string, panelId: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/storyboard/panels/${panelId}/control-bundle`);
  if (!res.ok) throw new Error(`Failed to fetch control bundle for panel ${panelId}`);
  return res.json();
}

export async function fetchProjectContinuity(projectId: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/storyboard/continuity`);
  if (!res.ok) throw new Error('Failed to fetch project continuity');
  return res.json();
}

export async function fetchStoryboardPage(
  projectId: string,
  pageNumber: number,
): Promise<{ page: any; total_pages: number; project_title: string }> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/storyboard/pages/${pageNumber}`);
  if (!res.ok) throw new Error(`Failed to fetch storyboard page ${pageNumber}`);
  return res.json();
}

export async function regeneratePanel(
  projectId: string,
  panelId: string,
  provider?: string,
): Promise<{ panel_id: string; panel_index: number; rendered_panel: any }> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/storyboard/regenerate-panel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ panel_id: panelId, provider }),
  });
  if (!res.ok) throw new Error('Failed to regenerate panel');
  return res.json();
}

export async function regeneratePanelVersion(
  projectId: string,
  panelId: string,
  provider?: string,
): Promise<{ panel_id: string; panel_index: number; version: number; panel: any; rendered_panel: any }> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/storyboard/panels/${panelId}/regenerate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider }),
  });
  if (!res.ok) throw new Error('Failed to regenerate panel version');
  return res.json();
}

export async function selectPanelVersion(
  projectId: string,
  panelId: string,
  version: number,
): Promise<{ panel_id: string; selected_version: number; panel: any }> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/storyboard/panels/${panelId}/select-version`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ version }),
  });
  if (!res.ok) throw new Error('Failed to select panel version');
  return res.json();
}

export async function regeneratePage(
  projectId: string,
  pageNumber: number,
  provider?: string,
): Promise<{ page_number: number; panels_count: number; rendered_panels: any[] }> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/storyboard/regenerate-page`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ page_number: pageNumber, provider }),
  });
  if (!res.ok) throw new Error('Failed to regenerate page');
  return res.json();
}

export function getAssetUrl(projectId: string, category: string, filename: string): string {
  return `${BASE_URL}/projects/${projectId}/storyboard/assets/${category}/${filename}`;
}

export async function fetchProviderStatus(): Promise<ProviderStatusResponse> {
  const res = await fetch(`${BASE_URL}/storyboard/provider-status`);
  if (!res.ok) {
    throw new Error('Failed to fetch provider status');
  }
  return res.json();
}

export async function externalRenderPanel(
  projectId: string,
  panelId: string,
  provider: string = 'huggingface',
  model?: string,
): Promise<{ panel_id: string; panel_index: number; version: number; panel: StoryboardPanel; rendered_panel: any }> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/storyboard/panels/${panelId}/external-render`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider, model }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'External render failed');
  }
  return res.json();
}

export async function externalRenderPage(
  projectId: string,
  pageNumber: number,
  provider: string = 'huggingface',
  model?: string,
): Promise<{ project_id: string; page_number: number; panels_rendered: number; shot_plan: any; rendered_panels: any[] }> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/storyboard/pages/${pageNumber}/external-render`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider, model }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'External render for page failed');
  }
  return res.json();
}

export async function fetchStructures(): Promise<{ structures: StructureDefinition[]; compatibility: Record<string, boolean> }> {
  const res = await fetch(`${BASE_URL}/structures`);
  if (!res.ok) throw new Error('Failed to fetch structures');
  return res.json();
}

export async function fetchBlueprint(projectId: string): Promise<StoryBlueprint> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/blueprint`);
  if (!res.ok) throw new Error('Failed to fetch story blueprint');
  return res.json();
}

export async function fetchCharacterArcs(projectId: string): Promise<Record<string, CharacterArcReport>> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/character-arcs`);
  if (!res.ok) throw new Error('Failed to fetch character arcs');
  return res.json();
}

export async function fetchCausalContinuity(projectId: string): Promise<CausalContinuitySummary> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/causal-continuity`);
  if (!res.ok) throw new Error('Failed to fetch causal continuity');
  return res.json();
}

export async function fetchScenes(projectId: string): Promise<any[]> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/scenes`);
  if (!res.ok) throw new Error('Failed to fetch scenes');
  return res.json();
}

// --- Phase A: Character Creation & Field Authority APIs ---

export async function intakeCharacter(
  projectId: string,
  rawText?: string,
  structuredPayload?: Record<string, any>,
  autoEnrich: boolean = false
): Promise<{ input: CharacterInput; draft: CharacterProfileDraft; completeness: CompletenessReport }> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/characters/intake`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      raw_text: rawText,
      structured_payload: structuredPayload,
      auto_enrich: autoEnrich,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to intake character' }));
    throw new Error(err.detail || 'Failed to intake character');
  }
  return res.json();
}

export async function fetchCharacterDrafts(
  projectId: string
): Promise<Array<{ draft: CharacterProfileDraft; completeness: CompletenessReport }>> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/characters/drafts`);
  if (!res.ok) throw new Error('Failed to fetch character drafts');
  return res.json();
}

export async function fetchCharacterDraft(
  projectId: string,
  draftId: string
): Promise<{ draft: CharacterProfileDraft; completeness: CompletenessReport }> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/characters/drafts/${draftId}`);
  if (!res.ok) throw new Error('Failed to fetch character draft');
  return res.json();
}

export async function enrichCharacterDraft(
  projectId: string,
  draftId: string
): Promise<{ draft: CharacterProfileDraft; completeness: CompletenessReport }> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/characters/drafts/${draftId}/enrich`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to enrich character draft');
  return res.json();
}

export async function lockCharacterField(
  projectId: string,
  draftId: string,
  fieldName: string
): Promise<{ draft: CharacterProfileDraft; field_name: string; authority: FieldAuthority }> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/characters/drafts/${draftId}/lock`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ field_name: fieldName }),
  });
  if (!res.ok) throw new Error('Failed to lock character field');
  return res.json();
}

export async function unlockCharacterField(
  projectId: string,
  draftId: string,
  fieldName: string
): Promise<{ draft: CharacterProfileDraft; field_name: string; authority: FieldAuthority }> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/characters/drafts/${draftId}/unlock`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ field_name: fieldName }),
  });
  if (!res.ok) throw new Error('Failed to unlock character field');
  return res.json();
}

export async function updateCharacterField(
  projectId: string,
  draftId: string,
  fieldName: string,
  value: any,
  authority: FieldAuthority = 'USER_LOCKED'
): Promise<{ draft: CharacterProfileDraft; completeness: CompletenessReport }> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/characters/drafts/${draftId}/update-field`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ field_name: fieldName, value, authority }),
  });
  if (!res.ok) throw new Error('Failed to update character field');
  return res.json();
}

export async function acceptCharacterDraft(
  projectId: string,
  draftId: string
): Promise<{ character: any; character_id: string; draft_id: string }> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/characters/drafts/${draftId}/accept`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to accept character' }));
    throw new Error(err.detail || 'Failed to accept character');
  }
  return res.json();
}

export async function getCharacterDynamics(
  projectId: string,
  characterId: string
): Promise<CharacterDynamicsProfile> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/characters/${characterId}/dynamics`);
  if (!res.ok) throw new Error('Failed to get character dynamics');
  return res.json();
}

export async function updateCharacterDynamics(
  projectId: string,
  characterId: string,
  dynamics: Partial<CharacterDynamicsProfile>,
  lockedFields?: string[],
  force?: boolean
): Promise<CharacterDynamicsProfile> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/characters/${characterId}/dynamics`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...dynamics, locked_fields: lockedFields, force }),
  });
  if (!res.ok) throw new Error('Failed to update character dynamics');
  return res.json();
}

export async function enrichCharacterDynamics(
  projectId: string,
  characterId: string
): Promise<CharacterDynamicsProfile> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/characters/${characterId}/dynamics/enrich`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to enrich character dynamics');
  return res.json();
}

export async function projectCharacterConsciousWant(
  projectId: string,
  characterId: string
): Promise<{ character_id: string; goal: any; conscious_want: string; dramatic_need: string; is_need_projected: boolean }> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/characters/${characterId}/project-want`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to project conscious want');
  return res.json();
}

export async function projectDraftConsciousWant(
  projectId: string,
  draftId: string
): Promise<{ draft: CharacterProfileDraft; completeness: CompletenessReport; conscious_want: string; is_need_projected: boolean }> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/characters/drafts/${draftId}/project-want`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to project draft conscious want');
  return res.json();
}
