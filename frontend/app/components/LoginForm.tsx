"use client";
import { useState } from "react";

export default function LoginForm({ onLogin }: { onLogin: (token: string, username: string) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [token, setToken] = useState("");

  const handleLogin = async () => {
    setError("");
    try {
      const res = await fetch(`http://${process.env.NEXT_PUBLIC_HOST_IP}:8000/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        throw new Error("Incorrect username or password");
      }

      const data = await res.json();
      setToken(data.access_token);
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("username", data.username);
      onLogin(data.access_token, data.username);
    } catch (err: any) {
      setError(err.message || "Login error");
    }
  };

  return (
    <div className="bg-white dark:bg-neutral-900 font-sans w-full">
      <div className="p-6 max-w-md mx-auto flex flex-col min-h-screen justify-center">
        {/* Welcome Header */}
        <div className="text-center mb-8 animate-fade-in">
          <div className="flex items-center justify-center mb-4">
            <h1 className="text-3xl font-black text-gray-800 dark:text-white">
              IHI Assistant
            </h1>
          </div>
          <p className="text-gray-600 dark:text-gray-300 text-sm leading-relaxed">
            Login with your company credentials to get started
          </p>
        </div>

        <input
          className="w-full p-4 mb-2 border border-neutral-300 dark:border-neutral-700 rounded-3xl shadow-lg mt-4"
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          className="w-full p-4 mb-2 border border-neutral-300 dark:border-neutral-700 rounded-3xl shadow-lg mt-4"
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button className="w-full bg-green-500 hover:bg-green-600 text-white p-4 rounded-3xl shadow-lg mt-4" onClick={handleLogin}>
          Log In
        </button>
        {error && <p className="text-red-500 mt-2">{error}</p>}
      </div>
    </div>
  );
}
