// Demo-only role selector for hackathon presentation. Not a real security/authentication system.
import React, { createContext, useContext, useState, useEffect } from "react";

export type Role = "patient" | "hospital";

export interface AuthContextType {
  role: Role | null;
  patientId: string | null;
  loginAsPatient: (id: string) => void;
  loginAsHospital: () => void;
  setPatientId: (id: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [role, setRole] = useState<Role | null>(() => {
    return (sessionStorage.getItem("demo_role") as Role) || null;
  });
  const [patientId, setPatientIdState] = useState<string | null>(() => {
    return sessionStorage.getItem("demo_patient_id") || "P001";
  });

  useEffect(() => {
    if (role) {
      sessionStorage.setItem("demo_role", role);
    } else {
      sessionStorage.removeItem("demo_role");
    }
  }, [role]);

  useEffect(() => {
    if (patientId) {
      sessionStorage.setItem("demo_patient_id", patientId);
    } else {
      sessionStorage.removeItem("demo_patient_id");
    }
  }, [patientId]);

  const loginAsPatient = (id: string) => {
    setRole("patient");
    setPatientIdState(id);
  };

  const loginAsHospital = () => {
    setRole("hospital");
  };

  const setPatientId = (id: string) => {
    setPatientIdState(id);
  };

  const logout = () => {
    setRole(null);
    setPatientIdState(null);
    sessionStorage.removeItem("demo_role");
    sessionStorage.removeItem("demo_patient_id");
  };

  return (
    <AuthContext.Provider value={{ role, patientId, loginAsPatient, loginAsHospital, setPatientId, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
