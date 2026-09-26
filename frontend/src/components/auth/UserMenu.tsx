"use client";

import React, { useState, useRef, useEffect } from "react";
import { LogOut, User as UserIcon } from "lucide-react";
import { signOut } from "../../lib/auth-client";

interface UserMenuProps {
  user: {
    id: string;
    name?: string | null;
    email?: string | null;
    image?: string | null;
  };
}

export const UserMenu: React.FC<UserMenuProps> = ({ user }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [imageError, setImageError] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Reset image error state whenever user or user.image changes
  useEffect(() => {
    setImageError(false);
  }, [user.image]);

  const displayName = user.name || user.email?.split("@")[0] || "Account";
  const initials = (
    displayName.includes(" ")
      ? displayName.split(" ").map((n) => n[0]).filter(Boolean).slice(0, 2).join("")
      : displayName.slice(0, 2)
  ).toUpperCase();

  const hasImage = Boolean(user.image && !imageError);

  // Close when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const handleSignOut = async () => {
    try {
      await signOut();
      window.location.reload();
    } catch (e) {
      console.error("Sign out error:", e);
    }
  };

  return (
    <div className="user-menu-container" ref={menuRef}>
      {/* Popover Card */}
      {isOpen && (
        <div className="user-popover-card">
          <div className="user-popover-header">
            <div className="user-avatar-circle">
              {hasImage ? (
                <img
                  src={user.image!}
                  alt={displayName}
                  className="user-avatar-img"
                  referrerPolicy="no-referrer"
                  onError={() => setImageError(true)}
                />
              ) : (
                <span>{initials}</span>
              )}
            </div>
            <div className="user-popover-info">
              <span className="user-popover-name" title={displayName}>
                {displayName}
              </span>
              {user.email && (
                <span className="user-popover-email" title={user.email}>
                  {user.email}
                </span>
              )}
            </div>
          </div>

          <div className="hairline-divider" style={{ margin: "8px 0" }} />

          <button
            className="user-popover-item"
            onClick={handleSignOut}
          >
            <LogOut size={14} />
            <span>Log out</span>
          </button>
        </div>
      )}

      {/* Trigger Button in Sidebar Footer */}
      <button
        className="user-menu-trigger"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Account menu"
      >
        <div className="user-avatar-circle">
          {hasImage ? (
            <img
              src={user.image!}
              alt={displayName}
              className="user-avatar-img"
              referrerPolicy="no-referrer"
              onError={() => setImageError(true)}
            />
          ) : (
            <span>{initials}</span>
          )}
        </div>
        <div className="user-trigger-info">
          <span className="user-trigger-name" title={displayName}>
            {displayName}
          </span>
        </div>
        <div className="user-trigger-badge">Free</div>
      </button>
    </div>
  );
};
