import { Navigate, useSearchParams } from "react-router-dom";
import { setToken } from "../api/client";

// Transient redirect target for GET /auth/google/callback on the backend.
// Stores the token before navigating away so ProtectedRoute's query on
// /dashboard picks it up immediately - doing this in an effect instead would
// race against <Navigate>'s own effect firing first.
export function AuthCallback() {
  const [params] = useSearchParams();
  const token = params.get("token");

  if (!token) return <Navigate to="/" replace />;

  setToken(token);
  return <Navigate to="/dashboard" replace />;
}
