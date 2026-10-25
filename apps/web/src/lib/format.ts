export const text = (v: unknown) =>
  v === null || v === undefined
    ? "—"
    : typeof v === "object"
      ? JSON.stringify(v)
      : String(v);

export const number = (v: unknown) => Number(v || 0).toLocaleString("en-IN");
