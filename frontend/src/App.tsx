import React from "react";
import { BrowserRouter, Routes, Route, Navigate, useParams } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { TwinProvider } from "./context/TwinContext";
import { Layout } from "./components/Layout";
import { LoginPage } from "./pages/LoginPage";
import { HospitalWardPage } from "./pages/HospitalWardPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DigitalTwinPage } from "./pages/DigitalTwinPage";
import { AgentSwarmPage } from "./pages/AgentSwarmPage";
import { RecoveryPlanPage } from "./pages/RecoveryPlanPage";
import { WhatIfPage } from "./pages/WhatIfPage";
import { ClinicianViewPage } from "./pages/ClinicianViewPage";

const RequireAuth: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { role } = useAuth();
  if (!role) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

const RootRedirect: React.FC = () => {
  const { role, patientId } = useAuth();
  if (!role) {
    return <Navigate to="/login" replace />;
  }
  if (role === "hospital") {
    return <Navigate to="/hospital" replace />;
  }
  return <Navigate to={`/patient/${patientId || "P001"}/dashboard`} replace />;
};

const AuthenticatedLayout: React.FC = () => {
  const { patientId: authPatientId } = useAuth();
  const { patientId: routePatientId } = useParams<{ patientId?: string }>();
  const activeId = routePatientId || authPatientId || "P001";

  return (
    <RequireAuth>
      <TwinProvider patientId={activeId}>
        <Layout />
      </TwinProvider>
    </RequireAuth>
  );
};

const PatientRouteWrapper: React.FC = () => {
  return (
    <Routes>
      <Route index element={<Navigate to="dashboard" replace />} />
      <Route path="dashboard" element={<DashboardPage />} />
      <Route path="twin" element={<DigitalTwinPage />} />
      <Route path="swarm" element={<AgentSwarmPage />} />
      <Route path="plan" element={<RecoveryPlanPage />} />
      <Route path="whatif" element={<WhatIfPage />} />
      <Route path="clinician" element={<ClinicianViewPage />} />
      <Route path="*" element={<Navigate to="dashboard" replace />} />
    </Routes>
  );
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route path="/" element={<AuthenticatedLayout />}>
            <Route index element={<RootRedirect />} />
            <Route path="hospital" element={<HospitalWardPage />} />
            <Route path="patient/:patientId/*" element={<PatientRouteWrapper />} />
            <Route path="*" element={<RootRedirect />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
