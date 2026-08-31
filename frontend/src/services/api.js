export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "");


export function requireApiBaseUrl() {
  if (!apiBaseUrl) {
    throw new Error("VITE_API_BASE_URL is not configured");
  }

  return apiBaseUrl;
}


export async function getBackendHealth(signal) {
  const response = await fetch(`${requireApiBaseUrl()}/health`, {
    signal,
  });

  if (!response.ok) {
    throw new Error(`Backend health request failed with ${response.status}`);
  }

  return response.json();
}
