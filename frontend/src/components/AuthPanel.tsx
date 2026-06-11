import { useState, type FormEvent } from "react";

type AuthPanelProps = {
  onLogin: (email: string, password: string) => Promise<void>;
  onRegister: (email: string, password: string, fullName: string) => Promise<void>;
  loading: boolean;
  error: string | null;
};

export function AuthPanel({ onLogin, onRegister, loading, error }: AuthPanelProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (mode === "login") {
      await onLogin(email, password);
    } else {
      await onRegister(email, password, fullName);
    }
  };

  return (
    <div className="auth-card">
      <div className="auth-header">
        <div>
          <p className="eyebrow">RAG AI Portal</p>
          <h1>{mode === "login" ? "Welcome back" : "Create an account"}</h1>
        </div>
        <div className="auth-toggle">
          <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")} type="button">
            Sign in
          </button>
          <button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")} type="button">
            Register
          </button>
        </div>
      </div>

      <form className="auth-form" onSubmit={submit}>
        <label>
          Email
          <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" placeholder="you@example.com" required />
        </label>

        {mode === "register" && (
          <label>
            Full name
            <input
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              type="text"
              placeholder="Your name"
              required
            />
          </label>
        )}

        <label>
          Password
          <input
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            type="password"
            placeholder="••••••••"
            minLength={8}
            required
          />
        </label>

        {error && <div className="alert">{error}</div>}

        <button className="primary-button" type="submit" disabled={loading}>
          {loading ? "Processing…" : mode === "login" ? "Sign in" : "Create account"}
        </button>
      </form>
    </div>
  );
}
