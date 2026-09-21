import { Navigate } from "react-router-dom";
import { googleLoginUrl } from "../api/client";
import { useCurrentUser } from "../hooks/useCurrentUser";

export function Login() {
  const { data: user, isLoading } = useCurrentUser();

  if (!isLoading && user) return <Navigate to="/dashboard" replace />;

  return (
    <div className="container" style={{ textAlign: "center", paddingTop: 120 }}>
      <h1>eng_cards</h1>
      <p className="muted">Карточки для изучения английских слов со spaced repetition.</p>
      <a className="btn" href={googleLoginUrl()} style={{ marginTop: 24 }}>
        Войти через Google
      </a>
    </div>
  );
}
