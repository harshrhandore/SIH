"use client";
import { useEffect, useState } from "react";
import { BookOpen, ArrowRight, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
type Account = { key: string; label: string; email: string; role: string };
export default function Login() {
  const [accounts, setAccounts] = useState<Account[]>([]),
    [showDemoAccounts, setShowDemoAccounts] = useState(false),
    [accountError, setAccountError] = useState(""),
    [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [error, setError] = useState(""),
    [pending, setPending] = useState(false);
  useEffect(() => {
    if (!showDemoAccounts || accounts.length) return;
    const controller = new AbortController();
    api<{ accounts: Account[] }>("/auth/demo-accounts", {
      signal: controller.signal,
    })
      .then((r) => {
        setAccounts(r.accounts);
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setAccountError(
            "Demo accounts are unavailable. You can still enter your email above.",
          );
      });
    return () => controller.abort();
  }, [showDemoAccounts, accounts.length]);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setPending(true);
    setError("");
    try {
      const r = await api<{ user: { role: string; student_id: string } }>(
        "/auth/login",
        { method: "POST", body: JSON.stringify({ email, password }) },
      );
      location.href =
        r.user.role === "STUDENT"
          ? "/students/" + r.user.student_id
          : r.user.role === "ADMIN"
            ? "/oversight"
            : r.user.role === "OFFICER"
              ? "/cases"
              : "/dashboard";
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPending(false);
    }
  }
  return (
    <main className="login">
      <section className="login-story">
        <div className="wordmark">
          <BookOpen size={30} /> SHIKSHAM <span>APAAR</span>
        </div>
        <div className="eyebrow">A SYNTHETIC ACADEMIC RECORD SYSTEM</div>
        <h1>
          Every record.
          <br />A clearer story.
        </h1>
        <p>
          Bring academic records together. Resolve discrepancies with human
          review. Carry the evidence forward.
        </p>
        <div className="rule" />
        <p className="small">
          <ShieldCheck size={18} /> Local consistency checks · Accountable
          decisions · Explainable evidence
        </p>
        <div className="folio">
          PROTOTYPE / SIH 26263 <span>01 — ACCESS</span>
        </div>
      </section>
      <section className="login-form">
        <div className="eyebrow">WELCOME TO THE LEDGER</div>
        <h2>Sign in to your workspace</h2>
        <p className="muted">Enter your email and password to continue.</p>
        <form onSubmit={submit}>
          <label>
            Email
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </label>
          {error ? (
            <div role="alert" className="error">
              {error}
            </div>
          ) : null}
          <button className="primary" disabled={pending}>
            {pending ? "Signing in…" : "Sign in"}
            <ArrowRight size={18} />
          </button>
        </form>
        <details
          className="login-demo"
          onToggle={(event) => {
            setShowDemoAccounts(event.currentTarget.open);
            setAccountError("");
          }}
        >
          <summary>Demo accounts</summary>
          <p className="muted">
            Choose a sample account to fill in your email, then sign in with
            your demo password.
          </p>
          {accountError ? (
            <p role="status">{accountError}</p>
          ) : accounts.length ? (
            <label>
              Demo account
              <select
                value={accounts.some((a) => a.email === email) ? email : ""}
                onChange={(event) => setEmail(event.target.value)}
              >
                <option value="" disabled>
                  Choose an account
                </option>
                {accounts.map((account) => (
                  <option key={account.key} value={account.email}>
                    {account.label}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <p role="status">Loading demo accounts…</p>
          )}
        </details>
        <p className="note">
          Synthetic data only. Local and mock checks do not establish official
          APAAR or issuer verification.
        </p>
      </section>
    </main>
  );
}
