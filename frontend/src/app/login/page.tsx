"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, setToken } from "@/lib/api";

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      const r = await api.login(email, password);
      setToken(r.access_token);
      router.push("/");
    } catch { setError("Invalid email or password."); }
  }
  return (
    <div className="card" style={{ maxWidth: 420, margin: "40px auto", padding: 28 }}>
      <h1 style={{ marginTop: 0 }}>Sign in</h1>
      <form onSubmit={submit} style={{ display: "grid", gap: 12 }}>
        <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
        <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" />
        <button className="btn-primary" type="submit">Sign in</button>
      </form>
      {error && <p style={{ color: "#f05a6c" }}>{error}</p>}
      <p style={{ color: "#929099" }}>No account? <a href="/register" style={{ color: "#f05a6c" }}>Register</a></p>
    </div>
  );
}
