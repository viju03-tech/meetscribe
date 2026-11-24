"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, setToken } from "@/lib/api";

export default function Register() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      const r = await api.register(email, password, name || undefined);
      setToken(r.access_token);
      router.push("/");
    } catch { setError("Registration failed — email may already be registered."); }
  }
  return (
    <div className="card" style={{ maxWidth: 420, margin: "40px auto", padding: 28 }}>
      <h1 style={{ marginTop: 0 }}>Create account</h1>
      <form onSubmit={submit} style={{ display: "grid", gap: 12 }}>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Display name (optional)" />
        <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
        <input type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password (min 8 characters)" />
        <button className="btn-primary" type="submit">Register</button>
      </form>
      {error && <p style={{ color: "#f05a6c" }}>{error}</p>}
      <p style={{ color: "#929099" }}>Already have an account? <a href="/login" style={{ color: "#f05a6c" }}>Sign in</a></p>
    </div>
  );
}
