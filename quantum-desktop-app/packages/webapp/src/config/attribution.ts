declare const __REPOSITORY_URL__: string;

function normalizeRepositoryUrl(url: string): string {
  const value = url.trim();
  if (!value) return "";
  if (value.startsWith("git@github.com:")) {
    return `https://github.com/${value.slice("git@github.com:".length).replace(/\.git$/, "")}`;
  }
  return value.replace(/\.git$/, "");
}

export const CREATOR = {
  name: "Trishan Ghosh",
  email: "ghoshtg17@gmail.com",
  instagram: "https://instagram.com/trishan_5668/",
} as const;

export const REPOSITORY_URL = normalizeRepositoryUrl(
  import.meta.env.VITE_REPOSITORY_URL ??
    import.meta.env.VITE_GITHUB_URL ??
    __REPOSITORY_URL__ ??
    "",
);

export const APP_TITLE = "QuantumLab — by Trishan Ghosh";

