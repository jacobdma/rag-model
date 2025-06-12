"use client";

import { useMsal } from "@azure/msal-react";

export default function LoginButton() {
    const { instance } = useMsal();

    const handleLogin = () => {
        instance.loginRedirect();
    };

    return <button onClick={handleLogin}>Sign in with Microsoft</button>;
}