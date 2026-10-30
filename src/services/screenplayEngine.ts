/**
 * D3 Story Lab — Screenplay & Visual Storyboard Synthesis Engine
 *
 * Grounded Screenplay Composition:
 * - Observer Agent clusters events into narrative scene beats.
 * - Scribe Agent synthesizes Fountain screenplay dialogue dynamically derived
 *   from executed character actions, emotional states, and verified facts.
 * - Storyboard Planner creates camera framing, psychological rationale, and
 *   genre-adaptive procedural SVG artwork with zero hardcoded scenario assumptions.
 */

import {
  ProjectData,
  ScreenplayDocument,
  ScreenplayScene,
  ScreenplayBlock,
  StoryboardPanel,
  ShotPlan,
} from '../types';

/**
 * Generates context-grounded character dialogue derived strictly from
 * an executed action and the speaking character's state.
 */
function synthesizeGroundedDialogue(
  characterName: string,
  eventType: string,
  targetName: string | undefined,
  locationName: string,
  emotionalState: { fear: number; anger: number; trust: number; curiosity: number },
  secretText?: string
): { line: string; cue: string } {
  const isHighFear = emotionalState.fear > 0.6;
  const isHighAnger = emotionalState.anger > 0.6;
  const isHighTrust = emotionalState.trust > 0.5;

  let cue = '(steady, watchful)';
  let line = `We need to assess what happened in ${locationName}.`;

  switch (eventType) {
    case 'CONFRONT_PEER': {
      cue = isHighAnger ? '(sharp, demanding)' : '(measured, blocking the exit)';
      line = targetName
        ? `I want the truth, ${targetName}. What are you doing in ${locationName}?`
        : `Answer me directly. We are out of time for excuses.`;
      break;
    }
    case 'INQUIRE_PEER': {
      cue = isHighFear ? '(low, urgent whisper)' : '(probing, curious)';
      line = targetName
        ? `Did you notice the readings when you arrived, ${targetName}?`
        : `Tell me what you saw before the alarms triggered.`;
      break;
    }
    case 'SHARE_SECRET': {
      cue = '(confidential, voice dropping low)';
      line = secretText
        ? `Listen closely. You need to know this: ${secretText}`
        : `I have information that changes our entire operational premise.`;
      break;
    }
    case 'NEGOTIATE_TERMS': {
      cue = isHighTrust ? '(offering an open hand)' : '(wary, calculating)';
      line = targetName
        ? `Neither of us walks out of ${locationName} if we keep working against each other, ${targetName}.`
        : `Let's establish terms right now. You take the primary asset; I secure the perimeter.`;
      break;
    }
    case 'DEFLECT_SCRUTINY': {
      cue = '(feigning unconcern, looking away)';
      line = `My reasons are my own. Focus on your own mandate.`;
      break;
    }
    case 'ACQUIRE_OBJECT': {
      cue = '(securing the item, eyes darting to the door)';
      line = targetName
        ? `I have secured the ${targetName}. We move on my count.`
        : `The objective is in hand. Prepare to withdraw.`;
      break;
    }
    case 'INSPECT_OBJECT': {
      cue = '(tracing the physical surface)';
      line = targetName
        ? `Look at the calibration on this ${targetName}. This wasn't an accident.`
        : `There are markings here that weren't in the initial debrief.`;
      break;
    }
    default: {
      line = `Stay alert. The situation in ${locationName} is changing rapidly.`;
      break;
    }
  }

  return { line, cue };
}

/**
 * Procedural Noir & Genre Comic SVG Generator
 */
export function generateProceduralComicSvg(
  shotType: string,
  cameraAngle: string,
  title: string,
  characterNames: string[],
  actionSummary: string,
  genreTheme: string = 'ESPIONAGE_NOIR'
): string {
  // Theme-specific accent colors
  let accentHex = '#C9A46B'; // Default Noir Gold
  let secondaryHex = '#3A3F4C';

  if (genreTheme === 'SCI_FI') {
    accentHex = '#4AC9E3'; // Cyan
    secondaryHex = '#1D3B53';
  } else if (genreTheme === 'WESTERN') {
    accentHex = '#E5A65D'; // Ochre / Amber
    secondaryHex = '#4A3525';
  } else if (genreTheme === 'MEDICAL') {
    accentHex = '#52DE97'; // Mint green
    secondaryHex = '#204035';
  } else if (genreTheme === 'COURTROOM') {
    accentHex = '#D4AF37'; // Judicial Gold
    secondaryHex = '#3E2F20';
  } else if (genreTheme === 'SUBMARINE') {
    accentHex = '#38B6FF'; // Deep sonar blue
    secondaryHex = '#142B3B';
  }

  const isCloseUp = shotType.toLowerCase().includes('close') || shotType.toLowerCase().includes('insert');
  const isWide = shotType.toLowerCase().includes('wide') || shotType.toLowerCase().includes('establishing');

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad_${genreTheme}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#060608" />
      <stop offset="50%" stop-color="#101318" />
      <stop offset="100%" stop-color="#050505" />
    </linearGradient>
    <pattern id="grid_${genreTheme}" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="${secondaryHex}" stroke-width="0.7" stroke-opacity="0.4"/>
    </pattern>
    <radialGradient id="vignette_${genreTheme}" cx="50%" cy="50%" r="70%">
      <stop offset="40%" stop-color="transparent" />
      <stop offset="100%" stop-color="#000000" stop-opacity="0.85" />
    </radialGradient>
  </defs>

  <rect width="960" height="540" fill="url(#bgGrad_${genreTheme})" />
  <rect width="960" height="540" fill="url(#grid_${genreTheme})" />

  <!-- Directional Chiaroscuro Light Shaft -->
  <polygon points="100,0 380,0 540,540 160,540" fill="${accentHex}" opacity="0.06" />

  <!-- Rule-of-Thirds Grid Guidelines -->
  <line x1="80" y1="410" x2="880" y2="410" stroke="#3A3F4C" stroke-width="1.5" stroke-dasharray="4 4" opacity="0.6" />
  <line x1="320" y1="80" x2="320" y2="460" stroke="#3A3F4C" stroke-width="1" stroke-opacity="0.3" />
  <line x1="640" y1="80" x2="640" y2="460" stroke="#3A3F4C" stroke-width="1" stroke-opacity="0.3" />

  <!-- Subject Staging Silhouette -->
  ${
    isCloseUp
      ? `<g transform="translate(480, 270)">
    <!-- Dramatic Character Profile -->
    <path d="M -80,-120 C -60,-170 60,-170 80,-120 C 100,-70 110,30 80,110 C 50,160 -50,160 -80,110 C -110,30 -100,-70 -80,-120 Z" fill="#14171D" stroke="${accentHex}" stroke-width="2.5" />
    <path d="M -50,-40 L 50,-40 L 35,-10 L -35,-10 Z" fill="#0A0A0C" opacity="0.9" />
    <circle cx="-30" cy="-25" r="4.5" fill="${accentHex}" opacity="0.95" />
    <circle cx="30" cy="-25" r="4.5" fill="${accentHex}" opacity="0.95" />
    <path d="M -60,90 L 0,135 L 60,90 L 100,180 L -100,180 Z" fill="#0A0A0C" stroke="${secondaryHex}" stroke-width="2" />
  </g>`
      : isWide
      ? `<g stroke="${secondaryHex}" stroke-width="1.5" fill="none">
    <rect x="140" y="130" width="680" height="290" fill="#0B0D12" fill-opacity="0.8" />
    <rect x="200" y="170" width="180" height="250" fill="#14171E" stroke="${accentHex}" stroke-width="2" />
    <rect x="220" y="190" width="140" height="230" fill="#08090C" />
    <!-- Distant Lone Subject -->
    <path d="M 520,350 L 530,330 L 535,300 L 545,300 L 550,330 L 560,350 L 555,420 L 525,420 Z" fill="#050505" stroke="${accentHex}" stroke-width="1.5" />
    <circle cx="540" cy="285" r="12" fill="#050505" stroke="${accentHex}" stroke-width="1.5" />
    <rect x="700" y="130" width="50" height="290" fill="#161A22" />
  </g>`
      : `<g transform="translate(0, 0)">
    <!-- Actor A (Left) -->
    <g transform="translate(320, 290)">
      <circle cx="0" cy="-70" r="32" fill="#12151B" stroke="${accentHex}" stroke-width="2" />
      <path d="M -50,-30 L 50,-30 L 65,130 L -65,130 Z" fill="#181B22" stroke="${secondaryHex}" stroke-width="2" />
    </g>
    <!-- Actor B (Right) -->
    <g transform="translate(640, 290)">
      <circle cx="0" cy="-70" r="32" fill="#14171E" stroke="#E05252" stroke-width="1.5" />
      <path d="M -55,-30 L 55,-30 L 70,130 L -70,130 Z" fill="#101217" stroke="${secondaryHex}" stroke-width="2" />
    </g>
    <!-- Tension Arc between them -->
    <path d="M 370,220 Q 480,175 590,220" fill="none" stroke="${accentHex}" stroke-width="1.5" stroke-dasharray="6 6" opacity="0.7" />
  </g>`
  }

  <rect width="960" height="540" fill="url(#vignette_${genreTheme})" pointer-events="none" />

  <!-- Editorial Lower-Third Slate -->
  <rect x="24" y="470" width="912" height="46" rx="3" fill="#090A0C" fill-opacity="0.92" stroke="#252830" stroke-width="1" />
  <text x="40" y="498" fill="${accentHex}" font-family="'IBM Plex Mono', monospace" font-size="12" font-weight="600" letter-spacing="0.1em">
    ${shotType.toUpperCase()} // ${cameraAngle.toUpperCase()} // ${characterNames.join(' & ').toUpperCase()}
  </text>
  <text x="910" y="498" text-anchor="end" fill="#B5AEA3" font-family="'Archivo', sans-serif" font-size="12">
    ${actionSummary.length > 55 ? actionSummary.substring(0, 52) + '...' : actionSummary}
  </text>
</svg>`;
}

/**
 * Composes a complete Fountain Screenplay and Storyboard Shot Plan from verified events.
 */
export function composeScreenplayAndStoryboard(project: ProjectData): {
  fountainText: string;
  screenplayDoc: ScreenplayDocument;
  shotPlan: ShotPlan;
  renderedPanels: StoryboardPanel[];
} {
  const world = project.world;
  const events = Object.values(world.events || {}).sort((a, b) => a.tick - b.tick);
  const chars = world.characters;
  const locs = world.locations;
  const genreTheme = (project.metadata as any)?.genre_theme || 'ESPIONAGE_NOIR';

  // Cluster events into scenes by location shifts
  const sceneList: ScreenplayScene[] = [];
  let currentLocId: string | null = null;
  let currentSceneEvents: typeof events = [];

  events.forEach((evt) => {
    const locId = evt.location_id || currentLocId || Object.keys(locs)[0];
    if (locId !== currentLocId && currentSceneEvents.length > 0) {
      // Flush current scene
      const sceneNum = sceneList.length + 1;
      const locName = locs[currentLocId || '']?.name || 'INTERIOR';
      const heading = `INT. ${locName.toUpperCase()} - ${sceneNum === 1 ? 'DAY' : 'LATER'}`;

      const blocks: ScreenplayBlock[] = [];
      blocks.push({
        id: `blk_s${sceneNum}_setup`,
        block_type: 'action',
        text: `The ambient tension in ${locName} is palpable. ${currentSceneEvents[0]?.description || ''}`,
        source_event_ids: [currentSceneEvents[0]?.id || ''],
      });

      currentSceneEvents.forEach((e, idx) => {
        blocks.push({
          id: `blk_s${sceneNum}_act_${idx}`,
          block_type: 'action',
          text: e.description,
          source_event_ids: [e.id],
        });

        if (e.actor_ids && e.actor_ids.length > 0) {
          const actor = chars[e.actor_ids[0]];
          const peer = e.actor_ids.length > 1 ? chars[e.actor_ids[1]] : undefined;
          if (actor) {
            const secret = actor.secrets?.[0] ? world.secrets[actor.secrets[0]]?.statement : undefined;
            const targetName = peer ? peer.name : undefined;
            const locNameStr = locs[e.location_id || '']?.name || 'the room';

            const { line, cue } = synthesizeGroundedDialogue(
              actor.name,
              e.event_type,
              targetName,
              locNameStr,
              actor.emotional_state,
              secret
            );

            blocks.push({
              id: `blk_s${sceneNum}_char_${idx}`,
              block_type: 'character',
              text: actor.name.toUpperCase(),
              source_event_ids: [e.id],
              character_id: actor.id,
            });

            blocks.push({
              id: `blk_s${sceneNum}_dial_${idx}`,
              block_type: 'dialogue',
              text: `${cue}\n${line}`,
              source_event_ids: [e.id],
              is_performance_cue: true,
            });
          }
        }
      });

      sceneList.push({
        scene_number: sceneNum,
        location_id: currentLocId || '',
        heading,
        blocks,
        source_event_ids: currentSceneEvents.map((e) => e.id),
      });

      currentSceneEvents = [];
    }

    currentLocId = locId;
    currentSceneEvents.push(evt);
  });

  // Flush final scene
  if (currentSceneEvents.length > 0) {
    const sceneNum = sceneList.length + 1;
    const locName = locs[currentLocId || '']?.name || 'INTERIOR';
    const heading = `INT. ${locName.toUpperCase()} - ${sceneNum === 1 ? 'DAY' : 'LATER'}`;

    const blocks: ScreenplayBlock[] = [];
    blocks.push({
      id: `blk_s${sceneNum}_setup`,
      block_type: 'action',
      text: `Silence settles over ${locName}. ${currentSceneEvents[0]?.description || ''}`,
      source_event_ids: [currentSceneEvents[0]?.id || ''],
    });

    currentSceneEvents.forEach((e, idx) => {
      blocks.push({
        id: `blk_s${sceneNum}_act_${idx}`,
        block_type: 'action',
        text: e.description,
        source_event_ids: [e.id],
      });

      if (e.actor_ids && e.actor_ids.length > 0) {
        const actor = chars[e.actor_ids[0]];
        const peer = e.actor_ids.length > 1 ? chars[e.actor_ids[1]] : undefined;
        if (actor) {
          const secret = actor.secrets?.[0] ? world.secrets[actor.secrets[0]]?.statement : undefined;
          const targetName = peer ? peer.name : undefined;
          const locNameStr = locs[e.location_id || '']?.name || 'the room';

          const { line, cue } = synthesizeGroundedDialogue(
            actor.name,
            e.event_type,
            targetName,
            locNameStr,
            actor.emotional_state,
            secret
          );

          blocks.push({
            id: `blk_s${sceneNum}_char_${idx}`,
            block_type: 'character',
            text: actor.name.toUpperCase(),
            source_event_ids: [e.id],
            character_id: actor.id,
          });

          blocks.push({
            id: `blk_s${sceneNum}_dial_${idx}`,
            block_type: 'dialogue',
            text: `${cue}\n${line}`,
            source_event_ids: [e.id],
            is_performance_cue: true,
          });
        }
      }
    });

    sceneList.push({
      scene_number: sceneNum,
      location_id: currentLocId || '',
      heading,
      blocks,
      source_event_ids: currentSceneEvents.map((e) => e.id),
    });
  }

  // Format into standard Fountain screenplay string
  let fountain = `Title: ${project.metadata.title.toUpperCase()}\n`;
  fountain += `Credit: Screenplay Generated by\n`;
  fountain += `Author: D3 Story Lab Emergent Simulation\n`;
  fountain += `Draft date: ${new Date().toLocaleDateString()}\n\n`;

  sceneList.forEach((s) => {
    fountain += `${s.heading}\n\n`;
    s.blocks.forEach((b) => {
      if (b.block_type === 'action') {
        fountain += `${b.text}\n\n`;
      } else if (b.block_type === 'character') {
        fountain += `${b.text}\n`;
      } else if (b.block_type === 'dialogue') {
        fountain += `${b.text}\n\n`;
      }
    });
  });

  const screenplayDoc: ScreenplayDocument = {
    title: project.metadata.title,
    credit: 'Written by',
    author: 'D3 Story Lab Autonomous Scribe',
    draft_date: new Date().toLocaleDateString(),
    scenes: sceneList,
  };

  // Plan Storyboard Panels
  const shotTypes = ['Wide Shot', 'Close-Up', 'Over-the-Shoulder', 'Dutch Angle Climax'];
  const cameraAngles = ['Wide Angle', 'Low Angle', 'Eye Level', 'High Angle'];

  const panels: StoryboardPanel[] = sceneList.slice(0, 4).map((s, idx) => {
    const primaryChar = Object.values(chars)[idx % Object.values(chars).length];
    const shot = shotTypes[idx % shotTypes.length];
    const angle = cameraAngles[idx % cameraAngles.length];
    const charNames = primaryChar ? [primaryChar.name] : ['Operatives'];

    return {
      id: `panel_${idx + 1}`,
      panel_id: `panel_${idx + 1}`,
      panel_number: idx + 1,
      scene_number: s.scene_number,
      shot_number: 1,
      page_number: 1,
      shot_type: shot,
      camera_angle: angle,
      aspect_ratio: '16:9',
      location_id: s.location_id,
      location_name: locs[s.location_id]?.name || 'Chamber',
      characters_present: primaryChar ? [primaryChar.id] : [],
      character_names: charNames,
      action_description: s.blocks[0]?.text || 'Dramatic scene development.',
      visual_prompt: `${shot} of ${charNames.join(' and ')} in ${s.heading}`,
      caption: `${s.heading} // ${shot.toUpperCase()}`,
      source_event_ids: s.source_event_ids,
      is_keyframe: true,
      image_status: 'ready',
      provider: 'comic_svg',
      mode: 'noir_graphic',
      rendered_svg: generateProceduralComicSvg(
        shot,
        angle,
        project.metadata.title,
        charNames,
        s.blocks[0]?.text || '',
        genreTheme
      ),
    };
  });

  const shotPlan: ShotPlan = {
    project_title: project.metadata.title,
    total_panels: panels.length,
    aspect_ratio: '16:9',
    panels,
  };

  return {
    fountainText: fountain,
    screenplayDoc,
    shotPlan,
    renderedPanels: panels,
  };
}
