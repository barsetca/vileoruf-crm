import { requireApiBaseUrl } from "./api.js";


async function request(path, accessToken, signal) {
  const response = await fetch(`${requireApiBaseUrl()}${path}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    signal,
  });
  if (!response.ok) throw new Error(`Reference data request failed with ${response.status}`);
  return response.json();
}


export const listPipelineStages = (accessToken, signal) => request("/pipeline-stages", accessToken, signal);
export const listEmployeeReferences = (accessToken, signal) => request("/employees/reference", accessToken, signal);
