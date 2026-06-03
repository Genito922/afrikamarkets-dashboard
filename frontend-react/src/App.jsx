import Navbar from "./components/Navbar";
import AppRoutes from "./routes";

export default function App() {
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
