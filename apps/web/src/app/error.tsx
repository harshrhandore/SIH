"use client";
export default function ErrorPage({
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <main id="main-content" className="boot">
      <h1>The ledger could not load</h1>
      <p>Your data is retained. Retry the request.</p>
      <button onClick={reset}>Retry</button>
    </main>
  );
}
