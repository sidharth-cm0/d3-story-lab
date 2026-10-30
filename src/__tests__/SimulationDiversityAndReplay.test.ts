import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  createNewProjectLogic,
  stepSimulationLogic,
  generateScreenplayLogic,
  replaySimulationLogic,
  alternativeRunLogic,
  generateDiversityReportLogic,
  simulationStore,
} from '../services/simulationEngine';
import { computeWorldFingerprint } from '../services/worldGenerator';

describe('D3 Story Lab — Simulation Diversity, Sovereignty & Replay Regression Suite', () => {

  it('1. Dossier Isolation: Non-dossier premises produce genre-authentic entities with zero Dossier fallbacks', () => {
    // Sci-Fi Premise
    const sciFiMeta = createNewProjectLogic({
      seedPrompt: 'At Europa Sub-Surface Outpost 4, astrobiologist Dr. Sarah Vance detects an unauthorized override on the airlock security locks while security chief Miller monitors incoming life-support telemetry.',
      title: 'Europa Protocol',
      seed: 44210,
    });

    const sciFiProject = simulationStore.getProject(sciFiMeta.id);
    assert.ok(sciFiProject, 'Sci-Fi project must exist in store');

    const charNames = Object.values(sciFiProject.world.characters).map((c) => c.name);
    const locNames = Object.values(sciFiProject.world.locations).map((l) => l.name);

    // Verify absence of hardcoded Dossier elements
    assert.ok(!locNames.includes('Archives Vault 409'), 'Must not spawn Archives Vault 409 in a Europa sci-fi premise');
    assert.ok(locNames.some((l) => l.toLowerCase().includes('outpost') || l.toLowerCase().includes('lab') || l.toLowerCase().includes('bay')),
      'Must spawn sci-fi premise-specific locations');

    // Western Premise
    const westernMeta = createNewProjectLogic({
      seedPrompt: 'U.S. Marshal Silas Thorne enters the Dusty Creek saloon with an unserved federal warrant, confronting cattle baron Vance Morgan in front of the town deputy.',
      title: 'High Noon at Dusty Creek',
      seed: 77123,
    });

    const westernProject = simulationStore.getProject(westernMeta.id);
    assert.ok(westernProject, 'Western project must exist');
    const westernLocs = Object.values(westernProject.world.locations).map((l) => l.name);
    assert.ok(westernLocs.some((l) => l.toLowerCase().includes('saloon') || l.toLowerCase().includes('office') || l.toLowerCase().includes('street')),
      'Must spawn western locations for western prompt');
    assert.ok(!westernLocs.includes('Archives Vault 409'), 'Must not contain Dossier vault in Western prompt');
  });

  it('2. Deterministic Seed Reproducibility: Identical premise + seed yields bit-exact state and event sequence', () => {
    const prompt = 'During an emergency containment lockdown at Metro General Hospital, Chief Surgeon Elena Alvarez discovers the experimental antiviral vial missing from the cold storage safe.';
    const fixedSeed = 88194;

    // Run A
    const metaA = createNewProjectLogic({
      seedPrompt: prompt,
      title: 'Hospital Lockdown Run A',
      seed: fixedSeed,
    });
    const projectA = simulationStore.getProject(metaA.id)!;
    const fpA = computeWorldFingerprint(projectA.world);

    // Run B (Independent run with identical seed)
    const metaB = createNewProjectLogic({
      seedPrompt: prompt,
      title: 'Hospital Lockdown Run B',
      seed: fixedSeed,
    });
    const projectB = simulationStore.getProject(metaB.id)!;
    const fpB = computeWorldFingerprint(projectB.world);

    // Initial state fingerprint must be bit-exact
    assert.equal(fpA, fpB, 'Initial state fingerprints must be 100% bit-exact for identical seed and premise');

    // Characters must be identical
    const charsA = Object.values(projectA.world.characters).map((c) => ({ name: c.name, role: c.role }));
    const charsB = Object.values(projectB.world.characters).map((c) => ({ name: c.name, role: c.role }));
    assert.deepEqual(charsA, charsB, 'Characters must match exactly between runs with identical seeds');

    // Advance both by 4 ticks deterministically
    const stepResA = stepSimulationLogic(metaA.id, 4);
    const stepResB = stepSimulationLogic(metaB.id, 4);

    assert.equal(stepResA.current_tick, stepResB.current_tick);
    assert.equal(stepResA.new_events.length, stepResB.new_events.length);

    // Compare event actions and descriptions tick by tick
    for (let i = 0; i < stepResA.new_events.length; i++) {
      const evA = stepResA.new_events[i];
      const evB = stepResB.new_events[i];
      assert.equal(evA.tick, evB.tick, `Event ${i} tick must match`);
      assert.equal(evA.event_type, evB.event_type, `Event ${i} type must match`);
      assert.equal(evA.description, evB.description, `Event ${i} description must match`);
    }
  });

  it('3. Seed Divergence: Identical premise with different seeds produces divergent worlds and trajectories', () => {
    const prompt = 'Within the neon-drenched server farm of OmniCorp Tower, data courier Jax Ren confronts corporate auditor Vane over an unencrypted black-budget neural imprint.';

    const metaSeed1 = createNewProjectLogic({
      seedPrompt: prompt,
      title: 'Cyberpunk Run 1',
      seed: 11111,
    });
    const project1 = simulationStore.getProject(metaSeed1.id)!;
    const fp1 = computeWorldFingerprint(project1.world);

    const metaSeed2 = createNewProjectLogic({
      seedPrompt: prompt,
      title: 'Cyberpunk Run 2',
      seed: 99999,
    });
    const project2 = simulationStore.getProject(metaSeed2.id)!;
    const fp2 = computeWorldFingerprint(project2.world);

    // Fingerprints must diverge
    assert.notEqual(fp1, fp2, 'Different seeds must produce different initial world fingerprints');

    // Advance both by 3 ticks
    const step1 = stepSimulationLogic(metaSeed1.id, 3);
    const step2 = stepSimulationLogic(metaSeed2.id, 3);

    // Descriptions should show procedural variation
    const desc1 = step1.new_events.map((e) => e.description).join(' ');
    const desc2 = step2.new_events.map((e) => e.description).join(' ');
    assert.notEqual(desc1, desc2, 'Different seeds must produce divergent action trajectories');
  });

  it('4. Grounded Screenplay Scribe: Dialogue and scene headings are grounded in premise with no canned Dossier lines', () => {
    const meta = createNewProjectLogic({
      seedPrompt: 'At Europa Sub-Surface Outpost 4, astrobiologist Dr. Sarah Vance detects an unauthorized override on the airlock security locks while security chief Miller monitors incoming life-support telemetry.',
      title: 'Europa Screenplay Test',
      seed: 33451,
    });

    // Advance 3 ticks so events occur
    stepSimulationLogic(meta.id, 3);

    const screenplayRes = generateScreenplayLogic(meta.id);
    assert.ok(screenplayRes.fountain_text.length > 50, 'Must produce non-empty Fountain screenplay');
    assert.ok(screenplayRes.total_scenes > 0, 'Must produce at least one scene');

    const lowerFountain = screenplayRes.fountain_text.toLowerCase();

    // Verify hardcoded Dossier strings are NOT present
    assert.ok(!lowerFountain.includes("the records don't lie, vincent"), 'Must not include hardcoded dossier line');
    assert.ok(!lowerFountain.includes("we were partners, evelyn"), 'Must not include hardcoded dossier line');
    assert.ok(!lowerFountain.includes("dossier vault 409"), 'Must not reference dossier vault');

    // Verify scene headings match generated locations
    const project = simulationStore.getProject(meta.id)!;
    const locNames = Object.values(project.world.locations).map((l) => l.name.toUpperCase());
    const hasMatchingScene = locNames.some((loc) => screenplayRes.fountain_text.toUpperCase().includes(loc));
    assert.ok(hasMatchingScene, 'Screenplay must contain scene headings corresponding to actual world locations');
  });

  it('5. Replay and Alternative Run Lifecycle: Replay reproduces history; Alternative run creates linked branch', () => {
    const metaOriginal = createNewProjectLogic({
      seedPrompt: 'Deep beneath the Arctic ice sheet, two rival drillers uncover a sealed titanium capsule.',
      title: 'Arctic Drillers',
      seed: 55432,
    });

    stepSimulationLogic(metaOriginal.id, 3);
    const origProject = simulationStore.getProject(metaOriginal.id)!;

    // Test Replay
    const replayed = replaySimulationLogic(metaOriginal.id);
    assert.equal(replayed.metadata.lifecycle_mode, 'replay');
    assert.equal(replayed.metadata.parent_simulation_id, metaOriginal.id);
    assert.equal(replayed.world.current_tick, origProject.world.current_tick);

    // Test Alternative Run
    const altMeta = alternativeRunLogic(metaOriginal.id, 99887);
    assert.equal(altMeta.lifecycle_mode, 'alternative_run');
    assert.equal(altMeta.parent_simulation_id, metaOriginal.id);
    assert.notEqual(altMeta.id, metaOriginal.id);

    // Test Diversity Report
    const report = generateDiversityReportLogic();
    assert.ok(report.total_simulations >= 3, 'Must track all generated simulations');
    assert.ok(report.unique_character_names.length >= 6, 'Must have distinct character names across simulations');
    assert.equal(typeof report.summary, 'string');
  });

});
