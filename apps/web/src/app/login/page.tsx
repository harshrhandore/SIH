"use client";
import { useEffect, useState } from "react";
import { BookOpen, ArrowRight } from "lucide-react";
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
    <main id="main-content" className="login" tabIndex={-1}>
      <section className="login-story">
        <div className="wordmark">
          <BookOpen size={27} aria-hidden="true" /> Shiksham <span>APAAR</span>
        </div>
        <p>Academic records</p>
      </section>
      <section className="login-form">
        <h1>Sign in</h1>
        <p className="muted">Enter your email and password to continue.</p>
        <form onSubmit={submit}>
          <label>
            Email
            <input
              type="email"
              name="email"
              spellCheck={false}
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
              name="password"
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
      </section>
    </main>
  );
}
