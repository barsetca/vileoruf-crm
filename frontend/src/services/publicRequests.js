import { requireApiBaseUrl } from "./api.js";


export async function createPublicRequest(payload) {
  const response = await fetch(`${requireApiBaseUrl()}/public/requests`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("Public request failed");
  return response.json();
}
