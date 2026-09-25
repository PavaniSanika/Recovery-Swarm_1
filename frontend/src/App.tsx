import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { TwinProvider } from "./context/TwinContext";
import { Layout } from "./components/Layout";
import { DashboardPage } from "./pages/DashboardPage";
import { DigitalTwinPage } from "./pages/DigitalTwinPage";
import { AgentSwarmPage } from "./pages/AgentSwarmPage";
import { RecoveryPlanPage } from "./pages/RecoveryPlanPage";
import { WhatIfPage } from "./pages/WhatIfPage";
import { ClinicianViewPage } from "./pages/ClinicianViewPage";

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <TwinProvider patientId="P001">
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<DashboardPage />} />
            <Route path="twin" element={<DigitalTwinPage />} />
            <Route path="swarm" element={<AgentSwarmPage />} />
            <Route path="plan" element={<RecoveryPlanPage />} />
            <Route path="whatif" element={<WhatIfPage />} />
            <Route path="clinician" element={<ClinicianViewPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </TwinProvider>
    </BrowserRouter>
  );
};

export default App;
