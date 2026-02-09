import { useState, useEffect } from 'react';

export function useAuth() {
    const [token, setToken] = useState<string | null>(null);
    const [username, setUsername] = useState<string | null>(null);
    const [isValidating, setIsValidating] = useState(true);

    useEffect(() => {
        const storedToken = localStorage.getItem("access_token");
        const storedUsername = localStorage.getItem("username");

        if (storedToken && storedUsername) {
            setToken(storedToken);
            setUsername(storedUsername);
        }
        setIsValidating(false);
    }, []);

    const login = (tok: string, user: string) => {
        setToken(tok);
        setUsername(user);
        localStorage.setItem("access_token", tok);
        localStorage.setItem("username", user);
    }

    const logout = () => {
        setToken(null);
        setUsername(null);
        localStorage.removeItem("access_token");
        localStorage.removeItem("username");
        localStorage.removeItem("password");
    }

    const handleUnauthorized = () => {
        logout();
        return false;
    }

    return {
        token,
        username,
        isAuthenticated: !!token,
        isValidating,
        login,
        logout,
        handleUnauthorized
    }
}