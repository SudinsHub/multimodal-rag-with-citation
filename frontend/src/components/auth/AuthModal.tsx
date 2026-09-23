"use client";

import React, { useState } from "react";
import { X, Loader2 } from "lucide-react";
import { signIn, signUp } from "../../lib/auth-client";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialMode?: "login" | "signup";
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  initialMode = "login",
}) => {
  const [mode, setMode] = useState<"login" | "signup">(initialMode);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setLoading(true);

    try {
      if (mode === "signup") {
        if (!name.trim()) {
          setErrorMessage("Please enter your name.");
          setLoading(false);
          return;
        }
        const res = await signUp.email({
          email,
          password,
          name,
        });
        if (res?.error) {
          setErrorMessage(res.error.message || "Failed to sign up.");
          setLoading(false);
          return;
        }
      } else {
        const res = await signIn.email({
          email,
          password,
        });
        if (res?.error) {
          setErrorMessage(res.error.message || "Invalid email or password.");
          setLoading(false);
          return;
        }
      }

      // Success
      setLoading(false);
      onClose();
      window.location.reload();
    } catch (err: any) {
      setErrorMessage(err.message || "An unexpected error occurred.");
      setLoading(false);
    }
  };

  const handleGoogleSignIn = async () => {
    setErrorMessage(null);
    setGoogleLoading(true);
    try {
      await signIn.social({
        provider: "google",
        callbackURL: window.location.href,
      });
    } catch (err: any) {
      setErrorMessage(err.message || "Google sign-in is not configured or failed.");
      setGoogleLoading(false);
    }
  };

  return (
    <div className="modal-scrim" onClick={onClose}>
      <div
        className="auth-modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-modal-title"
      >
        {/* Header */}
        <div className="auth-modal-header">
          <div>
            <h2 id="auth-modal-title" className="auth-modal-title">
              {mode === "login" ? "Welcome back" : "Create your account"}
            </h2>
            <p className="auth-modal-subtitle">
              {mode === "login"
                ? "Enter your details to access your workspace"
                : "Sign up to start chatting and indexing documents"}
            </p>
          </div>
          <button
            className="icon-btn"
            onClick={onClose}
            aria-label="Close auth dialog"
          >
            <X size={18} />
          </button>
        </div>

        {/* Error notification */}
        {errorMessage && (
          <div className="auth-error-banner">
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Google OAuth Button */}
        <button
          type="button"
          className="auth-social-btn"
          onClick={handleGoogleSignIn}
          disabled={googleLoading || loading}
        >
          {googleLoading ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <svg
              className="google-svg-icon"
              viewBox="0 0 24 24"
              width="16"
              height="16"
            >
              <path
                fill="currentColor"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="currentColor"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="currentColor"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
              />
              <path
                fill="currentColor"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
              />
            </svg>
          )}
          <span>Continue with Google</span>
        </button>

        {/* Restrained Hairline Divider */}
        <div className="auth-divider">
          <span className="auth-divider-line"></span>
          <span className="auth-divider-text">OR</span>
          <span className="auth-divider-line"></span>
        </div>

        {/* Email/Password Form */}
        <form onSubmit={handleEmailAuth} className="auth-form">
          {mode === "signup" && (
            <div className="form-group">
              <label className="form-label" htmlFor="auth-name">
                Full Name
              </label>
              <input
                id="auth-name"
                type="text"
                className="text-input"
                placeholder="Jane Doe"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                disabled={loading}
              />
            </div>
          )}

          <div className="form-group">
            <label className="form-label" htmlFor="auth-email">
              Email address
            </label>
            <input
              id="auth-email"
              type="email"
              className="text-input"
              placeholder="name@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="auth-password">
              Password
            </label>
            <input
              id="auth-password"
              type="password"
              className="text-input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            className="auth-submit-btn"
            disabled={loading || googleLoading}
          >
            {loading ? (
              <Loader2 size={16} className="animate-spin" />
            ) : mode === "login" ? (
              "Log in"
            ) : (
              "Sign up"
            )}
          </button>
        </form>

        {/* Mode Toggle Footer */}
        <div className="auth-footer-toggle">
          {mode === "login" ? (
            <span>
              Don't have an account?{" "}
              <button
                type="button"
                className="auth-link-btn"
                onClick={() => {
                  setErrorMessage(null);
                  setMode("signup");
                }}
              >
                Sign up
              </button>
            </span>
          ) : (
            <span>
              Already have an account?{" "}
              <button
                type="button"
                className="auth-link-btn"
                onClick={() => {
                  setErrorMessage(null);
                  setMode("login");
                }}
              >
                Log in
              </button>
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
