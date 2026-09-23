import { betterAuth } from "better-auth";
import { Pool } from "pg";

export const auth = betterAuth({
  database: new Pool({
    connectionString:
      process.env.DATABASE_URL ||
      "postgresql://postgres:postgrespassword@localhost:5432/construction_rag",
  }),
  emailAndPassword: {
    enabled: true,
    autoSignIn: true,
  },
  socialProviders: {
    google: {
      clientId: process.env.GOOGLE_CLIENT_ID || "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET || "",
      enabled: Boolean(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET),
    },
  },
  secret: process.env.BETTER_AUTH_SECRET || "development-secret-key-at-least-32-chars-long",
  baseURL: process.env.BETTER_AUTH_URL || "http://localhost:3000",
});
