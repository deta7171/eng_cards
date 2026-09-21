import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

export function Layout() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  async function handleLogout() {
    await api.post("/auth/logout");
    queryClient.setQueryData(["me"], null);
    navigate("/");
  }

  return (
    <div>
      <nav className="topbar">
        <strong>eng_cards</strong>
        <div className="links">
          <NavLink to="/dashboard" className={({ isActive }) => (isActive ? "active" : "")}>
            Дашборд
          </NavLink>
          <NavLink to="/words" className={({ isActive }) => (isActive ? "active" : "")}>
            Слова
          </NavLink>
          <NavLink to="/review" className={({ isActive }) => (isActive ? "active" : "")}>
            Повторение
          </NavLink>
          <button className="btn-secondary btn" onClick={handleLogout} style={{ padding: "4px 12px" }}>
            Выйти
          </button>
        </div>
      </nav>
      <div className="container">
        <Outlet />
      </div>
    </div>
  );
}
