import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center gap-6 text-center px-4">
      <span className="text-7xl">🌍</span>
      <h1 className="text-4xl font-bold text-white">404</h1>
      <p className="text-gray-400 max-w-sm">Cette page n'existe pas sur la carte des marchés africains.</p>
      <Link to="/" className="btn-primary">← Retour à l'accueil</Link>
    </div>
  );
}
