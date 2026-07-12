import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "./AuthProvider";

export function UserMenu(): JSX.Element {
  const { profile, user, openLogin, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onPointerDown = (event: PointerEvent) => {
      if (!ref.current?.contains(event.target as Node)) setOpen(false);
    };
    window.addEventListener("pointerdown", onPointerDown);
    return () => window.removeEventListener("pointerdown", onPointerDown);
  }, []);

  if (!user) {
    return (
      <button type="button" className="btn btn-secondary btn-sm" onClick={openLogin}>
        Login
      </button>
    );
  }

  const name = profile?.name ?? user.displayName ?? user.email ?? "Profile";
  const photoURL = profile?.photoURL || user.photoURL || "";
  const initial = name.slice(0, 1).toUpperCase();

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        className="avatar-button"
        onClick={() => setOpen((value) => !value)}
        aria-haspopup="menu"
        aria-expanded={open}
        title={name}
      >
        {photoURL ? <img src={photoURL} alt="" referrerPolicy="no-referrer" /> : <span>{initial}</span>}
      </button>
      {open && (
        <div className="avatar-menu" role="menu">
          <div className="avatar-menu-head">
            <strong>{name}</strong>
            <span>{profile?.email ?? user.email}</span>
          </div>
          <Link to="/profile" role="menuitem" onClick={() => setOpen(false)}>
            Profile
          </Link>
          <Link to="/settings" role="menuitem" onClick={() => setOpen(false)}>
            Settings
          </Link>
          <Link to="/history" role="menuitem" onClick={() => setOpen(false)}>
            Recent Circuits
          </Link>
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setOpen(false);
              void logout();
            }}
          >
            Logout
          </button>
        </div>
      )}
    </div>
  );
}

