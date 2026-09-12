import { ProjectMetadata, ProjectData, Event, StoryboardResponse, StoryOutline, StorySynopsis, ProviderStatusResponse } from './types';

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
  target_duration_minutes: number = 20
): Promise<ProjectMetadata> {
  const res = await fetch(`${BASE_URL}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      seed_prompt,
      title,
      input_type,
      target_duration_minutes,
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

export async function generateScreenplay(projectId: string): Promise<{ fountain_text: string; total_scenes: number; total_beats: number; total_panels?: number }> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/generate-screenplay`, {
    method: 'POST',
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
  if (!res.ok) throw new Error('Failed to fetch storyboard');
  return res.json();
}

export async function fetchVisualBible(projectId: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/visual-bible`);
  if (!res.ok) throw new Error('Failed to fetch visual bible');
  return res.json();
}

export async function planStoryboard(
  projectId: string,
  densityMode: string = 'standard',
  panelsPerPage: number = 4,
): Promise<StoryboardResponse> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/storyboard/plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ density_mode: densityMode, panels_per_page: panelsPerPage }),
  });
  if (!res.ok) throw new Error('Failed to plan storyboard');
  return res.json();
}

export async function generateStoryboard(
  projectId: string,
  provider?: string,
): Promise<StoryboardResponse> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/storyboard/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider }),
  });
  if (!res.ok) throw new Error('Failed to generate storyboard');
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
