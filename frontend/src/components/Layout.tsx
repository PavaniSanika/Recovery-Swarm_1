import React from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { DemoControlBar } from "./DemoControlBar";

export const Layout: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex font-sans antialiased">
      {/* Fixed Sidebar */}
      <Sidebar />

      {/* Main Container */}
      <div className="flex-1 pl-[240px] flex flex-col min-h-screen">
        {/* Top Demo Control Panel */}
        <div className="sticky top-0 z-20">
          <DemoControlBar />
        </div>

        {/* Page Content */}
        <main className="flex-1 p-4 sm:p-6 max-w-[1280px] w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
