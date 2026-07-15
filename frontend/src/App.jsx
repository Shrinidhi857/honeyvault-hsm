import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { VaultProvider, useVault } from "./context/VaultContext";
import { useAutoLock } from "./hooks/useAutoLock";
import Navbar from "./components/Navbar";
import Setup from "./pages/Setup";
import Unlock from "./pages/Unlock";
import Vault from "./pages/Vault";
import "./index.css";

// Separate component so it can access VaultContext
function AppRoutes() {
  const { unlocked, lock } = useVault();
  useAutoLock(unlocked, lock); // ← auto-lock hook

  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/" element={<Navigate to="/unlock" />} />
        <Route path="/setup" element={<Setup />} />
        <Route path="/unlock" element={<Unlock />} />
        <Route path="/vault" element={<Vault />} />
      </Routes>
    </>
  );
}

export default function App() {
  return (
    <VaultProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </VaultProvider>
  );
}