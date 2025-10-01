"use client";
import { useState } from "react";

export default function LoginForm({
  onLogin,
  onGuest,
}: {
  onLogin: (token: string, username: string) => void;
  onGuest: () => void;
}){
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [token, setToken] = useState("");

  const handleLogin = async () => {
    setError("");
    try {
      const res = await fetch(`http://${process.env.NEXT_PUBLIC_HOST_IP}:${process.env.NEXT_PUBLIC_BACKEND_PORT}/login`, {
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
      localStorage.setItem("password", data.password);
      onLogin(data.access_token, data.username);
    } catch (err: any) {
      setError(err.message || "Login error");
    }
  };

  return (
    <div className="bg-white dark:bg-neutral-900 font-medium w-full h-screen justify-center items-center flex font-sans">
      <div className="p-10 rounded-xl w-sm mx-auto flex flex-col justify-center border border-neutral-300 dark:border-neutral-700 ">
        {/* Welcome Header */}
        <div className="text-center mb-8 animate-fade-in">
          <div className="flex items-center justify-center mb-4">
            <h1 className="text-responsive-3xl font-black text-neutral-800 dark:text-neutral-100">
              IHI Assistant
            </h1>
          </div>
        </div>

        <input
          className="w-full px-3 py-2 mb-4 rounded-lg focus:outline-none
                 bg-neutral-200 dark:bg-neutral-700 text-neutral-800 dark:text-neutral-100"
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />

        <input
          className="w-full px-3 py-2 mb-2 rounded-lg focus:outline-none
                 bg-neutral-200 dark:bg-neutral-700 text-neutral-800 dark:text-neutral-100"
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <button 
          className="w-full bg-green-500 hover:bg-green-600 text-white px-3 py-2 rounded-lg mt-8
                 transition-colors duration-200" 
          onClick={handleLogin}
        >
          Log In
        </button>

        <button
          className="text-responsive-base text-neutral-700 dark:text-neutral-300 mt-4 transition-colors duration-200 hover:underline"
          onClick={onGuest}
          type="button"
        >
          Continue as Guest
        </button>

        {error && <p className="text-red-500 dark:text-red-400 text-responsive-sm mt-4 text-center">{error}</p>}
      </div>
    </div>
  );
}
