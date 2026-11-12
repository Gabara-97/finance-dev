// Public values only. The anon key is designed to be public (Row Level Security protects data).
// NEVER put the service-role key, database password or any secret here.
export const CONFIG = {
  SUPABASE_URL: "https://YOUR-PROJECT.supabase.co",
  SUPABASE_ANON_KEY: "YOUR-PUBLIC-ANON-KEY",
  API_BASE_URL: "http://localhost:5000/api/v1", // set to your Render URL + /api/v1 in production
  CURRENCY: "ZAR",
  LOCALE: "en-ZA",
};
