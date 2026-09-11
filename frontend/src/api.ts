import { ProjectMetadata, ProjectData, Event, StoryboardResponse } from './types';

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

export async function createProject(seed_prompt: string, title?: string): Promise<ProjectMetadata> {
  const res = await fetch(`${BASE_URL}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ seed_prompt, title }),
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

export async function generateScreenplay(projectId: string): Promise<{ fountain_text: string; total_scenes: number; total_beats: number }> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/generate-screenplay`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to generate screenplay');
  return res.json();
}

export function getDownloadUrl(projectId: string): string {
  return `${BASE_URL}/projects/${projectId}/screenplay/download`;
}

export async function fetchStoryboard(projectId: string): Promise<StoryboardResponse> {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/storyboard`);
  if (!res.ok) throw new Error('Failed to fetch storyboard');
  return res.json();
}

