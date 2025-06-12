import { Configuration } from "@azure/msal-browser";

export const msalConfig: Configuration = {
    auth: {
        clientId: "YOUR_CLIENT_ID",
        authority: "https://login.microsoftonline.com/Yf8cdef31-a31e-4b4a-93e4-5f571e91255a",
        redirectUri: "http://192.168.3.93:3000", // or localhost for testing
    },
};