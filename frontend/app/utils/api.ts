export function getBackendUrl() {
  const host = process.env.NEXT_PUBLIC_HOST_IP;
  const port = process.env.NEXT_PUBLIC_BACKEND_PORT || '8000';
  return `http://${host}:${port}`;
}