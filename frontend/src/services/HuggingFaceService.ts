/**
 * HuggingFaceService.ts
 *
 * Frontend service delegating external AI render requests to the secure D3 backend.
 * Credentials (HF_TOKEN) are maintained exclusively on the server and never
 * exposed in client-side bundles or network payloads.
 */

import { externalRenderPanel, externalRenderPage } from '../api';
import { StoryboardPanel } from '../types';

export const DEFAULT_HF_MODEL = 'stabilityai/stable-diffusion-xl-base-1.0';

export const PRICING_DISCLAIMER =
  'Optional external provider. Availability, quotas and pricing depend on the provider/account.';

export interface ExternalRenderResult {
  panelId: string;
  version: number;
  panel: StoryboardPanel;
  renderedPanel: any;
}

/**
 * Triggers server-side external image rendering for a single panel.
 * The D3 backend makes the outbound call using server-side HF_TOKEN and persists
 * the resulting asset via StoryboardAssetStore.
 */
export async function requestExternalPanelRender(
  projectId: string,
  panelId: string,
  model: string = DEFAULT_HF_MODEL,
): Promise<ExternalRenderResult> {
  const res = await externalRenderPanel(projectId, panelId, 'huggingface', model);
  return {
    panelId: res.panel_id,
    version: res.version,
    panel: res.panel,
    renderedPanel: res.rendered_panel,
  };
}

/**
 * Triggers server-side external image rendering for all panels on a single page only.
 * Never automatically executes across entire multi-page projects.
 */
export async function requestExternalPageRender(
  projectId: string,
  pageNumber: number,
  model: string = DEFAULT_HF_MODEL,
): Promise<{ projectId: string; pageNumber: number; panelsRendered: number }> {
  const res = await externalRenderPage(projectId, pageNumber, 'huggingface', model);
  return {
    projectId: res.project_id,
    pageNumber: res.page_number,
    panelsRendered: res.panels_rendered,
  };
}
