const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

export async function fetchJson<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}/api/v1${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
  
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(url, {
      credentials: "include",
      ...options,
      headers,
    });
  } catch {
    throw new Error("Unable to connect to the server. Please check your network connection.");
  }

  if (!response.ok) {
    let errorDetail = "";
    try {
      const data = await response.json();
      if (data.detail) {
        if (typeof data.detail === "string") {
          errorDetail = data.detail;
        } else if (Array.isArray(data.detail)) {
          errorDetail = data.detail
            .map((item: any) => item.msg || item.message || JSON.stringify(item))
            .join("; ");
        } else {
          errorDetail = JSON.stringify(data.detail);
        }
      } else if (data.message) {
        errorDetail = data.message;
      }
    } catch {
      // ignore json parse error
    }

    if (!errorDetail) {
      if (response.status === 401) {
        errorDetail = "Please log in to continue.";
      } else if (response.status === 403) {
        errorDetail = "You do not have permission to access this resource.";
      } else if (response.status === 404) {
        errorDetail = "The requested resource was not found.";
      } else if (response.status === 429) {
        errorDetail = "Too many requests. Please wait a moment and try again.";
      } else if (response.status >= 500) {
        errorDetail = "The server is temporarily unavailable. Please try again shortly.";
      } else {
        errorDetail = `Request failed (${response.status}). Please try again.`;
      }
    }
    throw new Error(errorDetail);
  }

  if (response.status === 204) {
    return null as T;
  }

  return response.json();
}
