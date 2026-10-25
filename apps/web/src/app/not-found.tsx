import Link from "next/link";
export default function NotFound() {
  return (
    <main className="boot">
      <h1>Record unavailable</h1>
      <p>The requested page is unavailable in this workspace.</p>
      <Link href="/login">Return to sign in</Link>
    </main>
  );
}
