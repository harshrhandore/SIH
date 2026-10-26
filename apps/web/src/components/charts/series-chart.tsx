"use client";
import { useId } from "react";

export type Point = { label: string; value: number };

export function SeriesChart({
  title,
  points,
  caption,
  maximum,
  suffix = "",
  mode = "bars",
}: {
  title: string;
  points: Point[];
  caption: string;
  maximum?: number;
  suffix?: string;
  mode?: "bars" | "line";
}) {
  const id = useId();
  if (!points.length)
    return (
      <div className="empty">
        <h3>{title}</h3>
        <p>No data for the selected filters.</p>
      </div>
    );
  const top = Math.max(1, maximum ?? Math.max(...points.map((p) => p.value)));
  const slot = 540 / points.length;
  const x = (index: number) => 60 + slot * (index + 0.5);
  const y = (value: number) => 210 - (value / top) * 170;
  const format = (value: number) =>
    value.toLocaleString("en-IN", { maximumFractionDigits: suffix ? 1 : 0 }) +
    suffix;
  return (
    <figure className="analytics-chart">
      <h2 id={id + "-title"}>{title}</h2>
      <svg
        viewBox="0 0 640 260"
        role="img"
        aria-labelledby={id + "-title " + id + "-summary"}
      >
        {[0, 0.25, 0.5, 0.75, 1].map((tick) => (
          <g key={tick}>
            <line
              x1="60"
              x2="600"
              y1={y(top * tick)}
              y2={y(top * tick)}
              stroke="var(--border)"
            />
            <text
              x="50"
              y={y(top * tick) + 4}
              textAnchor="end"
              className="chart-label"
            >
              {format(top * tick)}
            </text>
          </g>
        ))}
        {mode === "line" ? (
          <path
            d={points
              .map((point, i) => `${i ? "L" : "M"}${x(i)},${y(point.value)}`)
              .join(" ")}
            fill="none"
            stroke="var(--teal, #0a6467)"
            strokeWidth="3"
          />
        ) : null}
        {points.map((point, index) => (
          <g key={point.label}>
            <title>
              {point.label}: {format(point.value)}
            </title>
            {mode === "line" ? (
              <circle cx={x(index)} cy={y(point.value)} r="4" fill="#0a6467" />
            ) : (
              <rect
                x={x(index) - Math.min(56, slot * 0.6) / 2}
                y={y(point.value)}
                width={Math.min(56, slot * 0.6)}
                height={210 - y(point.value)}
                rx="3"
                fill={index % 2 ? "#9c7835" : "#0a6467"}
              />
            )}
            <text
              x={x(index)}
              y="234"
              textAnchor="middle"
              className="chart-label"
            >
              {point.label}
            </text>
          </g>
        ))}
      </svg>
      <figcaption>{caption}</figcaption>
      <dl id={id + "-summary"} className="chart-summary">
        {points.map((point) => (
          <div key={point.label}>
            <dt>{point.label}</dt>
            <dd>{format(point.value)}</dd>
          </div>
        ))}
      </dl>
    </figure>
  );
}
