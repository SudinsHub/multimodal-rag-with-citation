/**
 * Standardized Error Normalization Utility for Construction RAG.
 * 
 * Ensures users receive clear, appropriate, and actionable messages across all layers:
 * - Authentication & Login / Signup
 * - Input Security & Guardrails
 * - Document Upload & Validation
 * - RAG Query & AI Inference
 * - Database & Network Connectivity
 * 
 * Prevents raw internal leaks (e.g. "user table not found", "relation 'user' does not exist")
 * while avoiding unhelpful vague messages (e.g. "Something went wrong").
 */

export type ErrorContext = "auth" | "chat" | "upload" | "document" | "general";

/**
 * Normalizes any error object, string, or status into an appropriate, standard user-facing message.
 */
export function formatUserErrorMessage(error: unknown, context: ErrorContext = "general"): string {
  if (!error) {
    return "An unexpected issue occurred. Please try again.";
  }

  // Extract raw string message
  let raw = "";
  if (typeof error === "string") {
    raw = error;
  } else if (error instanceof Error) {
    raw = error.message;
  } else if (typeof error === "object" && error !== null) {
    const errObj = error as Record<string, any>;
    raw = errObj.message || errObj.detail || errObj.error || JSON.stringify(error);
  }

  const lower = raw.toLowerCase();

  // 1. Guardrail & Security Notices (already specifically worded for the user)
  if (
    raw.startsWith("Security Notice:") ||
    raw.startsWith("Rate limit reached:") ||
    raw.startsWith("Session prompt limit reached:") ||
    raw.startsWith("Document limit reached:") ||
    raw.startsWith("Upload rate limit reached:") ||
    raw.startsWith("Query is too long") ||
    raw.startsWith("Query exceeds") ||
    raw.startsWith("Query cannot be empty") ||
    raw.startsWith("File exceeds") ||
    raw.startsWith("Encrypted or password-protected") ||
    raw.startsWith("The uploaded PDF") ||
    raw.startsWith("Invalid file format") ||
    raw.startsWith("Only PDF files")
  ) {
    return raw;
  }

  // 2. Database & Schema Internals (e.g. "user table not found", "relation 'user' does not exist")
  if (
    lower.includes("user table not found") ||
    lower.includes("relation \"user\" does not exist") ||
    lower.includes("relation 'user' does not exist") ||
    lower.includes("relation \"session\" does not exist") ||
    lower.includes("table not found") ||
    lower.includes("relation") && lower.includes("does not exist") ||
    lower.includes("undefinedtable") ||
    lower.includes("syntax error at or near") ||
    lower.includes("psycopg2") ||
    lower.includes("sqlalchemy")
  ) {
    if (context === "auth") {
      return "The authentication service is initializing. Please wait a few seconds and try again.";
    }
    return "The database service is temporarily unavailable. Please try again shortly.";
  }

  // 3. Network & Connection Issues
  if (
    lower.includes("failed to fetch") ||
    lower.includes("networkerror") ||
    lower.includes("econnrefused") ||
    lower.includes("connection refused") ||
    lower.includes("network request failed") ||
    lower.includes("fetch failed")
  ) {
    return "Unable to connect to the service. Please check your internet connection or try again in a moment.";
  }

  // 4. Authentication Layer (Better-Auth, Login, Signup, OAuth)
  if (context === "auth" || lower.includes("auth") || lower.includes("password") || lower.includes("credential")) {
    if (
      lower.includes("invalid_email_or_password") ||
      lower.includes("invalid email or password") ||
      lower.includes("invalid credentials") ||
      lower.includes("wrong password")
    ) {
      return "Incorrect email or password. Please verify your credentials and try again.";
    }

    if (
      lower.includes("user_already_exists") ||
      lower.includes("user already exists") ||
      lower.includes("email already in use") ||
      lower.includes("already registered")
    ) {
      return "An account with this email address already exists. Please log in instead.";
    }

    if (
      lower.includes("password_too_short") ||
      lower.includes("password must be at least") ||
      lower.includes("password is too short")
    ) {
      return "Password must be at least 6 characters long.";
    }

    if (lower.includes("invalid_email") || lower.includes("invalid email")) {
      return "Please enter a valid email address (e.g. name@example.com).";
    }

    if (lower.includes("google") || lower.includes("oauth") || lower.includes("social")) {
      return "Google sign-in could not be completed. Please check your browser popup/cookie settings or log in with email.";
    }

    if (lower.includes("session expired") || lower.includes("token expired")) {
      return "Your session has expired. Please log in again to continue.";
    }
  }

  // 5. Authorization & Permission
  if (
    lower.includes("401") ||
    lower.includes("unauthorized") ||
    lower.includes("authentication required")
  ) {
    return "Please log in to proceed with this action.";
  }

  if (lower.includes("403") || lower.includes("forbidden") || lower.includes("permission denied")) {
    return "You do not have permission to access or modify this resource.";
  }

  // 6. Rate Limiting & Quotas (429)
  if (lower.includes("429") || lower.includes("too many requests") || lower.includes("rate limit")) {
    if (context === "chat") {
      return "Rate limit reached: Maximum 5 chat messages per minute. Please pause for a moment before asking another question.";
    }
    if (context === "upload") {
      return "Upload rate limit reached: Please wait 30 seconds between document uploads.";
    }
    return "Too many requests. Please pause a moment before trying again.";
  }

  // 7. Not Found (404)
  if (lower.includes("404") || lower.includes("not found")) {
    if (context === "document") return "The requested document was not found.";
    if (context === "chat") return "The requested conversation was not found.";
    return "The requested resource could not be found.";
  }

  // 8. Payload Too Large (413)
  if (lower.includes("413") || lower.includes("payload too large") || lower.includes("entity too large")) {
    return "The uploaded file exceeds the 10MB maximum limit. Please select a smaller PDF.";
  }

  // 9. AI / LLM / Gemini Inference & Provider Errors
  if (
    lower.includes("quota") ||
    lower.includes("resourceexhausted") ||
    lower.includes("overloaded") ||
    lower.includes("model is busy")
  ) {
    return "The AI service is temporarily experiencing high demand (quota reached). Please wait a moment and try again.";
  }

  if (lower.includes("safety") || lower.includes("blocked") || lower.includes("finish_reason")) {
    return "The assistant could not complete the response due to content safety policies. Please rephrase your query.";
  }

  // 10. HTTP 500 / 502 / 503 / 504 Gateway / Server Errors
  if (
    lower.includes("500 internal server error") ||
    lower.includes("internal server error") ||
    lower.includes("502 bad gateway") ||
    lower.includes("503 service unavailable") ||
    lower.includes("504 gateway timeout")
  ) {
    return "The server is temporarily busy or unavailable. Please try again shortly.";
  }

  // 11. Code / Runtime Tracebacks (sanitize raw python or JS traces)
  if (
    lower.includes("traceback (most recent call last)") ||
    lower.includes("keyerror") ||
    lower.includes("typeerror") ||
    lower.includes("attributeerror") ||
    lower.includes("zerodivisionerror") ||
    lower.includes("nullpointer") ||
    lower.includes("undefined is not an object")
  ) {
    return "An internal processing error occurred. Please try again in a few moments.";
  }

  // Clean and return raw message if it's already a concise, helpful sentence
  const trimmed = raw.replace(/^request failed: \d+\s*/i, "").trim();
  if (trimmed.length > 5 && trimmed.length < 200 && !trimmed.includes("{") && !trimmed.includes("[")) {
    return trimmed;
  }

  return "An issue occurred while processing your request. Please try again.";
}
