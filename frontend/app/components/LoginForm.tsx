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
    <div className="bg-neutral-100 dark:bg-neutral-900 font-medium w-full h-screen justify-center items-center flex">
      <div className="bg-white dark:bg-neutral-800 p-10 rounded-3xl shadow-xl w-sm mx-auto flex flex-col justify-center">
        {/* Welcome Header */}
        <div className="text-center mb-8 animate-fade-in">
          <div className="flex items-center justify-center mb-4">
            <h1 className="text-responsive-3xl font-black text-neutral-800 dark:text-neutral-100">
              IHI Assistant
            </h1>
          </div>
        </div>

        <p className="text-neutral-600 dark:text-neutral-300 text-responsive-sm font-medium leading-relaxed mt">
          Company username
        </p>
        <input
          className="w-full px-3 py-2 mb-2 border border-neutral-300 dark:border-neutral-700 rounded-md 
                 bg-neutral-200 dark:bg-neutral-700 text-neutral-800 dark:text-neutral-100
                 focus:outline-none focus:ring-2 focus:ring-green-500 dark:focus:ring-green-600"
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />

        <p className="text-neutral-600 dark:text-neutral-300 text-responsive-sm font-medium leading-relaxed mt-4">
          Password
        </p>
        <input
          className="w-full px-3 py-2 mb-2 border border-neutral-300 dark:border-neutral-700 rounded-md
                 bg-neutral-200 dark:bg-neutral-700 text-neutral-800 dark:text-neutral-100
                 focus:outline-none focus:ring-2 focus:ring-green-500 dark:focus:ring-green-600"
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <div className="mt-6 border-t border-neutral-200 dark:border-neutral-700" />

        <button 
          className="w-full bg-green-500 hover:bg-green-600 text-white p-3 rounded-3xl mt-8
                 transition-colors duration-200" 
          onClick={handleLogin}
        >
          Log In
        </button>

        <p className="p-3 text-responsive-lg text-center text-neutral-600 dark:text-neutral-400">OR</p>

        <button
          className="w-full bg-neutral-200 dark:bg-neutral-700 hover:bg-neutral-300 
                 dark:hover:bg-neutral-600 text-neutral-800 dark:text-neutral-100 
                 p-3 rounded-3xl mt-2 transition-colors duration-200"
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
