#!/usr/bin/env node
// Tracked S08 hasher replica. Imports the live GSD engine hasher at runtime.
// Does not copy the hash loop. Does not write tracked files.
import { homedir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

function engineRoot() {
  const fromEnv = process.env.GSD_HOME;
  if (fromEnv) return join(fromEnv, "agent", "extensions", "gsd");
  return join(homedir(), ".gsd", "agent", "extensions", "gsd");
}

async function loadEngine() {
  const root = engineRoot();
  const hasherUrl = pathToFileURL(join(root, "verification-source-integrity.js")).href;
  const prefsUrl = pathToFileURL(join(root, "preferences.js")).href;
  const hasher = await import(hasherUrl);
  const prefs = await import(prefsUrl);
  if (typeof hasher.captureMilestoneVerificationSourceRevision !== "function") {
    throw new Error("engine hasher export captureMilestoneVerificationSourceRevision is missing");
  }
  if (typeof prefs.loadEffectiveGSDPreferences !== "function") {
    throw new Error("engine preferences export loadEffectiveGSDPreferences is missing");
  }
  return { hasher, prefs };
}

async function main() {
  const cwd = process.cwd();
  const { hasher, prefs } = await loadEngine();
  const loaded = prefs.loadEffectiveGSDPreferences(cwd);
  const preferences = loaded?.preferences ?? loaded ?? {};
  const captured = hasher.captureMilestoneVerificationSourceRevision(cwd, preferences);
  if (!captured || captured.ok !== true || typeof captured.sourceRevision !== "string") {
    const error = captured?.error || "engine hasher returned a non-ok snapshot";
    process.stdout.write(`${JSON.stringify({ ok: false, error })}\n`);
    process.exit(1);
  }
  const sourceRevision = captured.sourceRevision;
  if (!/^sha256:[0-9a-f]{64}$/.test(sourceRevision)) {
    process.stdout.write(
      `${JSON.stringify({ ok: false, error: `unexpected sourceRevision shape: ${sourceRevision}` })}\n`,
    );
    process.exit(1);
  }
  process.stdout.write(`${JSON.stringify({ ok: true, source_revision: sourceRevision })}\n`);
}

main().catch((error) => {
  process.stdout.write(`${JSON.stringify({ ok: false, error: String(error?.message || error) })}\n`);
  process.exit(1);
});
