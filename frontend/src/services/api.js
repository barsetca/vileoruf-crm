const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;


export async function getBackendHealth(signal) {
  if (!apiBaseUrl) {
    throw new Error("VITE_API_BASE_URL is not configured");
  }

  const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}/health`, {
    signal,
  });

  if (!response.ok) {
    throw new Error(`Backend health request failed with ${response.status}`);
  }

  return response.json();
}
