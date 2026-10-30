/**
 * StoryboardPromptBuilder.ts
 *
 * Compiles ShotData (action, camera angle, emotion) and VisualBible
 * (character descriptions, location, props) into a dense, cinematic text prompt
 * for open-source generative models (e.g. SDXL) via Hugging Face Inference API.
 */

import {
  StoryboardPanel,
  VisualBible,
  CharacterVisualReference,
  LocationVisualReference,
  ObjectVisualReference,
} from '../types';

/**
 * Flexible ShotData interface supporting both raw shot structures
 * and existing StoryboardPanel models.
 */
export interface ShotData {
  id?: string;
  panel_id?: string;
  shot_type?: string;
  camera_angle?: string;
  action?: string;
  action_description?: string;
  emotion?: string;
  mood?: string;
  characters_present?: string[];
  character_names?: string[];
  objects_in_frame?: string[];
  location_id?: string;
  location_name?: string;
  lighting?: string;
  dialogue?: string;
  dialogue_excerpt?: string | null;
  subject_focus?: string;
  visual_description?: string;
  lens_feel?: string;
  subtext_context?: string;
}

/**
 * Mandatory style tags required for consistent graphite sketch storyboards.
 */
export const MANDATORY_STYLE_TAGS =
  'professional storyboard panel, graphite pencil sketch, rough cross-hatching, highly detailed, high contrast, grayscale cinematic composition, masterpiece.';

/**
 * Default negative prompt eliminating colors, digital CGI gloss, and anatomical deformities.
 */
export const DEFAULT_NEGATIVE_PROMPT =
  'color, saturation, 3d render, cgi, photorealistic skin, digital gloss, anime, cartoon, deformed hands, extra fingers, missing fingers, distorted face, blurry, text, watermark, signature, speech bubbles, low resolution, poorly drawn.';

/**
 * Maps raw camera angle tags to descriptive prompt language.
 */
function mapCameraAngle(angle?: string): string {
  if (!angle) return 'eye-level cinematic angle';
  const clean = angle.toLowerCase().replace(/_/g, ' ');
  switch (clean) {
    case 'low angle':
      return 'dramatic low-angle shot looking up with imposing perspective';
    case 'high angle':
      return 'high-angle perspective looking down';
    case 'dutch angle':
      return 'dynamic Dutch tilt camera angle with tense tilted horizon';
    case 'bird eye':
      return 'overhead top-down bird-eye view';
    case 'eye level':
    default:
      return 'straight eye-level cinematic framing';
  }
}

/**
 * Maps raw shot type tags to framing scale descriptions.
 */
function mapShotType(type?: string): string {
  if (!type) return 'medium shot';
  const clean = type.toLowerCase().replace(/_/g, ' ');
  switch (clean) {
    case 'close up':
      return 'intense cinematic close-up shot capturing nuanced facial acting and eyes';
    case 'extreme close up':
      return 'extreme close-up macro shot focusing tightly on expression and eyes';
    case 'wide':
      return 'wide establishing shot showing full architectural environment and subjects';
    case 'extreme wide':
      return 'extreme wide panoramic establishing shot with expansive background';
    case 'over shoulder':
      return 'over-the-shoulder medium shot with foreground silhouette framing';
    case 'insert':
      return 'detailed insert shot of key prop held in hands with meticulous focus';
    case 'reaction':
      return 'reaction close-up shot capturing sudden emotional realization';
    case 'medium':
    default:
      return 'cinematic medium shot framed from waist up';
  }
}

export class StoryboardPromptBuilder {
  /**
   * Compiles ShotData and optional VisualBible into a dense, descriptive text prompt.
   */
  public static buildPrompt(
    shot: ShotData | StoryboardPanel,
    bible?: VisualBible | null
  ): string {
    const parts: string[] = [];

    // 1. Core Framing & Shot Scale
    const shotTypeDesc = mapShotType(shot.shot_type);
    const cameraAngleDesc = mapCameraAngle(shot.camera_angle);
    parts.push(`${shotTypeDesc}, ${cameraAngleDesc}`);

    // 2. Primary Action & Narrative Core
    const actionText =
      shot.action_description ||
      shot.action ||
      shot.visual_description ||
      '';
    if (actionText.trim()) {
      parts.push(`Action: ${actionText.trim()}`);
    }

    // 3. Subject Focus & Performance Subtext
    if (shot.subject_focus) {
      parts.push(`Subject focus: ${shot.subject_focus}`);
    }

    // 4. Emotional Tone & Facial Acting
    const rawShot = shot as ShotData;
    const emotionalCue = rawShot.emotion || rawShot.mood;
    if (emotionalCue) {
      parts.push(`Mood and facial acting: ${emotionalCue} with subtle psychological micro-expressions`);
    }

    const dialogueText = rawShot.dialogue_excerpt || rawShot.dialogue;
    if (dialogueText) {
      const line = String(dialogueText).replace(/"/g, '');
      parts.push(`Dialogue beat: "${line}"`);
    }

    // 5. Characters from VisualBible
    const charIds = shot.characters_present || [];
    const charDescriptions: string[] = [];

    if (bible && bible.characters) {
      for (const cid of charIds) {
        const ref: CharacterVisualReference | undefined = bible.characters[cid];
        if (ref) {
          const traits: string[] = [];
          if (ref.build) traits.push(ref.build);
          if (ref.face_features) traits.push(ref.face_features);
          if (ref.hair) traits.push(`hair: ${ref.hair}`);
          if (ref.clothing) traits.push(`wardrobe: ${ref.clothing}`);
          if (ref.signature_props && ref.signature_props.length > 0) {
            traits.push(`carrying ${ref.signature_props.join(', ')}`);
          }
          const traitsStr = traits.length > 0 ? ` (${traits.join(', ')})` : '';
          charDescriptions.push(`Character ${ref.name}${traitsStr}`);
        }
      }
    }

    // Fallback if characters not in bible but named in shot
    if (charDescriptions.length === 0 && shot.character_names && shot.character_names.length > 0) {
      charDescriptions.push(`Characters: ${shot.character_names.join(', ')}`);
    }

    if (charDescriptions.length > 0) {
      parts.push(charDescriptions.join('; '));
    }

    // 6. Environment / Location from VisualBible
    let locationAdded = false;
    if (bible && bible.locations && shot.location_id && bible.locations[shot.location_id]) {
      const locRef: LocationVisualReference = bible.locations[shot.location_id];
      const locTraits: string[] = [];
      if (locRef.environment_type) locTraits.push(locRef.environment_type);
      if (locRef.architecture) locTraits.push(locRef.architecture);
      if (locRef.key_landmarks && locRef.key_landmarks.length > 0) {
        locTraits.push(`landmarks: ${locRef.key_landmarks.join(', ')}`);
      }
      const locDetails = locTraits.length > 0 ? ` (${locTraits.join(', ')})` : '';
      parts.push(`Environment: ${locRef.name}${locDetails}`);
      locationAdded = true;
    }

    if (!locationAdded && (shot.location_name || shot.location_id)) {
      parts.push(`Environment: ${shot.location_name || shot.location_id}`);
    }

    // 7. Props in Frame from VisualBible
    const propIds = shot.objects_in_frame || [];
    if (bible && bible.objects && propIds.length > 0) {
      const propDescriptions: string[] = [];
      for (const pid of propIds) {
        const objRef: ObjectVisualReference | undefined = bible.objects[pid];
        if (objRef) {
          const rawObj = objRef as unknown as { visual_description?: string; form_factor?: string; materials?: string };
          const pDesc = rawObj.visual_description || rawObj.form_factor || rawObj.materials || '';
          propDescriptions.push(`${objRef.name}${pDesc ? ` (${pDesc})` : ''}`);
        }
      }
      if (propDescriptions.length > 0) {
        parts.push(`Key props: ${propDescriptions.join(', ')}`);
      }
    }

    // 8. Lighting & Atmospheric Setup
    if (shot.lighting) {
      parts.push(`Lighting: ${shot.lighting}`);
    } else {
      parts.push('Lighting: dramatic chiaroscuro single key lighting with deep pencil cast shadows');
    }

    // 9. Mandatory Professional Storyboard Style Tags
    parts.push(MANDATORY_STYLE_TAGS);

    return parts.join('. ').replace(/\.\./g, '.');
  }

  /**
   * Returns standard negative prompt.
   */
  public static buildNegativePrompt(): string {
    return DEFAULT_NEGATIVE_PROMPT;
  }

  /**
   * Compiles both positive prompt and negative prompt for immediate API consumption.
   */
  public static compile(
    shot: ShotData | StoryboardPanel,
    bible?: VisualBible | null
  ): { prompt: string; negativePrompt: string } {
    return {
      prompt: this.buildPrompt(shot, bible),
      negativePrompt: this.buildNegativePrompt(),
    };
  }
}

/**
 * Functional export alias for direct functional programming usage.
 */
export const buildStoryboardPrompt = (
  shot: ShotData | StoryboardPanel,
  bible?: VisualBible | null
): string => StoryboardPromptBuilder.buildPrompt(shot, bible);

export const buildNegativePrompt = (): string =>
  StoryboardPromptBuilder.buildNegativePrompt();
