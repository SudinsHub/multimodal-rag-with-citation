import { auth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";
import { NextRequest } from "next/server";

const handlers = toNextJsHandler(auth);

let migrationPromise: Promise<void> | null = null;

async function ensureMigrated() {
  if (!migrationPromise) {
    migrationPromise = (async () => {
      try {
        const { getMigrations } = await import("better-auth/db/migration");
        const { toBeCreated, toBeAdded, runMigrations } = await getMigrations(auth.options);
        if (toBeCreated.length > 0 || toBeAdded.length > 0) {
          console.log(
            `[BetterAuth] Schema mismatch detected (${toBeCreated.length} tables to create, ${toBeAdded.length} fields to add). Running auto-migrations...`
          );
          await runMigrations();
          console.log("[BetterAuth] Migrations executed successfully.");
        }
      } catch (err) {
        console.error("[BetterAuth] Auto-migration error:", err);
      }
    })();
  }
  await migrationPromise;
}

export async function GET(request: NextRequest) {
  await ensureMigrated();
  return handlers.GET(request);
}

export async function POST(request: NextRequest) {
  await ensureMigrated();
  return handlers.POST(request);
}

