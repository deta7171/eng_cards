import { Navigate, Outlet } from "react-router-dom";
import { useCurrentUser } from "../hooks/useCurrentUser";

export function ProtectedRoute() {
  const { data: user, isLoading } = useCurrentUser();

  if (isLoading) return <div className="container muted">Загрузка…</div>;
  if (!user) return <Navigate to="/" replace />;

  return <Outlet />;
}
