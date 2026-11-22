type Size = "sm" | "md" | "lg";

const PARTS = /^(.)(\d{3})(..)(\d{2,3})$/;

const FLAGS: Record<string, string> = {
  RU: "RUS",
  KZ: "KZ",
  BY: "BY",
  UZ: "UZ",
  AE: "UAE",
};

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
  const match = PARTS.exec(code.replace(/\s/g, ""));
  const style = glow ? { boxShadow: `0 0 34px ${glow}55, 0 0 2px ${glow}99` } : undefined;
  const flag = FLAGS[country] ?? "RUS";

  if (!match) {
    return (
      <div className={`plate plate-${size} ${className}`} style={style}>
        <span className="plate-fallback">{code}</span>
      </div>
    );
  }

  const [, first, digits, tail, region] = match;
  return (
    <div className={`plate plate-${size} ${className}`} style={style}>
      <div className="plate-main">
        <span className="plate-letter">{first}</span>
        <span className="plate-digits">{digits}</span>
        <span className="plate-letter">{tail}</span>
      </div>
      <div className="plate-side">
        <span className="plate-rus">{flag}</span>
        <span className="plate-flag" aria-hidden="true" />
        <span className="plate-region">{region}</span>
      </div>
    </div>
  );
}
