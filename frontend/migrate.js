const { Pool } = require("pg");
const { getMigrations } = require("better-auth/db/migration");

async function run() {
  const connectionString =
    process.env.DATABASE_URL ||
    "postgresql://postgres:postgrespassword@localhost:5432/construction_rag";

  const safeUrl = connectionString.replace(/:[^:@]+@/, ":****@");
  console.log(`[BetterAuth] Connecting to database: ${safeUrl}`);

  const pool = new Pool({ connectionString });

  const authOptions = {
    database: pool,
    emailAndPassword: { enabled: true },
    socialProviders: {
      google: {
        clientId: process.env.GOOGLE_CLIENT_ID || "temp_id",
        clientSecret: process.env.GOOGLE_CLIENT_SECRET || "temp_secret",
      },
    },
  };

  try {
    const { toBeCreated, toBeAdded, runMigrations } = await getMigrations(authOptions);
    console.log(
      `[BetterAuth] Tables to create: ${toBeCreated.length} (${toBeCreated.map((t) => t.table).join(", ") || "none"})`
    );
    console.log(`[BetterAuth] Fields to add: ${toBeAdded.length}`);

    if (toBeCreated.length > 0 || toBeAdded.length > 0) {
      await runMigrations();
      console.log("[BetterAuth] Migrations applied successfully!");
    } else {
      console.log("[BetterAuth] All tables already exist and match schema.");
    }
  } catch (error) {
    console.error("[BetterAuth] Migration failed:", error);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

run();
