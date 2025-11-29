import React from "react";
import { Outlet } from "react-router-dom";

const Layout = () => {
  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <Outlet />
    </div>
  );
};

export default Layout;
