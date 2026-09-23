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
  const menuRef = useRef<HTMLDivElement>(null);

  const displayName = user.name || user.email?.split("@")[0] || "Account";
  const initials = displayName.slice(0, 2).toUpperCase();

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
              {user.image ? (
                <img src={user.image} alt={displayName} className="user-avatar-img" />
              ) : (
                <span>{initials}</span>
              )}
            </div>
            <div className="user-popover-info">
              <span className="user-popover-name">{displayName}</span>
              <span className="user-popover-email">{user.email}</span>
            </div>
          </div>

          <div className="hairline-divider" style={{ margin: "6px 0" }} />

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
          {user.image ? (
            <img src={user.image} alt={displayName} className="user-avatar-img" />
          ) : (
            <span>{initials}</span>
          )}
        </div>
        <div className="user-trigger-info">
          <span className="user-trigger-name">{displayName}</span>
        </div>
        <div className="user-trigger-badge">Free</div>
      </button>
    </div>
  );
};
