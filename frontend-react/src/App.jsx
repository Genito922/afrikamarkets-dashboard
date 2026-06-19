import { useState } from "react";
import Navbar from "./components/Navbar";
import AppRoutes from "./routes";
import Onboarding from "./pages/Onboarding";

export default function App() {
  const [onboardingDone, setOnboardingDone] = useState(
    () => localStorage.getItem("onboarding_done") === "true"
  );

  const handleOnboardingComplete = () => {
    localStorage.setItem("onboarding_done", "true");
    setOnboardingDone(true);
  };

  if (!onboardingDone) {
    return <Onboarding onComplete={handleOnboardingComplete} />;
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1">
        <AppRoutes />
      </main>
      <footer className="border-t border-gray-800 py-6 text-center text-sm text-gray-500">
        © {new Date().getFullYear()} Afrika Markets Intelligence · All rights reserved
      </footer>
    </div>
  );
}
