type Size = "sm" | "md" | "lg";

const RU = /^(.)(\d{3})(..)(\d{2,3})$/;
const KZ = /^(\d{3})([A-Z]{3})(\d{2})$/;
const BY = /^(\d{4})([А-ЯІ]{2})(\d)$/;
const UZ = /^(\d{2})([A-Z])(\d{3})([A-Z]{2})$/;
const AE = /^([A-Z]{1,2})(\d{1,5})$/;

const FLAGS: Record<string, string> = {
  RU: "RUS",
  KZ: "KZ",
  BY: "BY",
  UZ: "UZ",
  AE: "UAE",
};

function split(code: string, country: string) {
  const clean = code.replace(/[\s-]/g, "").toUpperCase();

  if (country === "KZ") {
    const m = KZ.exec(clean);
    return m ? { head: m[1], mid: m[2], tail: "", region: m[3] } : null;
  }
  if (country === "BY") {
    const m = BY.exec(clean);
    return m ? { head: m[1], mid: m[2], tail: "", region: m[3] } : null;
  }
  if (country === "UZ") {
    const m = UZ.exec(clean);
    return m
      ? { head: "", mid: `${m[2]}${m[3]}`, tail: m[4], region: m[1], leading: true }
      : null;
  }
  if (country === "AE") {
    const m = AE.exec(clean);
    return m ? { head: m[1], mid: m[2], tail: "", region: "" } : null;
  }

  const m = RU.exec(clean);
  if (m) return { head: m[1], mid: m[2], tail: m[3], region: m[4] };
  return null;
}

export function Plate({
  code,
  size = "md",
  glow,
  country = "RU",
  className = "",
}: {
  code: string;
  size?: Size;
  glow?: string;
  country?: string;
  className?: string;
}) {
  const parsed = split(code, country);
  const style = glow ? { boxShadow: `0 0 34px ${glow}55, 0 0 2px ${glow}99` } : undefined;
  const flag = FLAGS[country] ?? "RUS";

  if (!parsed) {
    return (
      <div className={`plate plate-${size} ${className}`} style={style}>
        <span className="plate-fallback">{code}</span>
      </div>
    );
  }

  return (
    <div className={`plate plate-${size} plate-${country.toLowerCase()} ${className}`} style={style}>
      {parsed.leading && parsed.region && (
        <span className="plate-region-block">{parsed.region}</span>
      )}
      <div className="plate-main">
        <span className="plate-letter">{parsed.head}</span>
        <span className="plate-digits">{parsed.mid}</span>
        {parsed.tail && <span className="plate-letter">{parsed.tail}</span>}
      </div>
      <div className="plate-side">
        <span className="plate-rus">{flag}</span>
        <span
          className={`plate-flag plate-flag-${country.toLowerCase()}`}
          aria-hidden="true"
        />
        {!parsed.leading && parsed.region && (
          <span className="plate-region">{parsed.region}</span>
        )}
      </div>
    </div>
  );
}
