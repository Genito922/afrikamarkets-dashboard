/**
 * ComplianceBanner — composant unique de conformité réglementaire
 *
 * Variants :
 *   "strip"   → badge inline (navbar, header)
 *   "compact" → ligne unique (bas de page, footer de section)
 *   "full"    → bloc complet (landing page, onboarding)
 */

export default function ComplianceBanner({ variant = "compact", className = "" }) {
  if (variant === "strip") {
    return (
      <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full
                       bg-gray-900 border border-gray-700 ${className}`}>
        <span className="w-1.5 h-1.5 rounded-full bg-yellow-500" />
        <span className="text-xs text-gray-500">Outil indépendant · Non-conseil</span>
      </div>
    );
  }

  if (variant === "compact") {
    return (
      <p className={`text-xs text-gray-600 text-center leading-relaxed ${className}`}>
        ⚠ Outil d'analyse indépendant — non affilié à la BRVM ni à l'AMF-UMOA.
        Les informations présentées ne constituent pas un conseil en investissement.
        Investir comporte un risque de perte en capital.
      </p>
    );
  }

  // variant === "full"
  return (
    <div className={`flex items-start gap-3 px-4 py-3.5 rounded-xl
                     bg-yellow-950/20 border border-yellow-900/30 ${className}`}>
      <span className="text-yellow-500 shrink-0 mt-0.5 text-base">⚠</span>
      <div className="text-xs text-yellow-200/60 leading-relaxed">
        <strong className="text-yellow-300">Avertissement légal — </strong>
        Afrika Markets Intelligence est un outil d'analyse et d'information indépendant,
        non affilié à la Bourse Régionale des Valeurs Mobilières (BRVM), à l'AMF-UMOA,
        au DC/BR ni à aucune autorité financière officielle de l'UEMOA.
        Les données, signaux et analyses présentés sont à titre informatif et éducatif uniquement
        et{" "}
        <strong className="text-yellow-300">
          ne constituent pas un conseil en investissement
        </strong>{" "}
        au sens réglementaire.
        Tout investissement comporte un risque de perte en capital, pouvant aller jusqu'à la perte totale.
        Les performances passées ne préjugent pas des performances futures.
        Consultez un professionnel financier agréé avant toute décision d'investissement.
      </div>
    </div>
  );
}
