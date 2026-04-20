import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./context/AuthContext";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import PatientDashboardPage from "./pages/PatientDashboardPage";

function ProtectedRoute({ children, role }: { children: JSX.Element; role: "doctor" | "patient" }) {
  const { token, user } = useAuth();
  if (!token || !user) {
    return <Navigate to="/login" replace />;
  }
  if (user.role !== role) {
    return <Navigate to={user.role === "patient" ? "/patient" : "/"} replace />;
  }
  return children;
}

export default function App() {
  const { token, user } = useAuth();

  return (
    <Routes>
      <Route
        path="/login"
        element={token ? <Navigate to={user?.role === "patient" ? "/patient" : "/"} replace /> : <LoginPage />}
      />
      <Route
        path="/"
        element={
          <ProtectedRoute role="doctor">
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/patient"
        element={
          <ProtectedRoute role="patient">
            <PatientDashboardPage />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
