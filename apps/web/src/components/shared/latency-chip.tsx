export function LatencyChip({
  cache,
  tookMs,
}: {
  cache: unknown;
  tookMs: unknown;
}) {
  const elapsed = Number(tookMs);
  return (
    <span className="mono" aria-label="Backend search timing">
      {Number.isFinite(elapsed)
        ? elapsed.toFixed(2) + " ms API time"
        : "Timing unavailable"}{" "}
      · {String(cache || "Uncached")}
      <small> Network time excluded.</small>
    </span>
  );
}
