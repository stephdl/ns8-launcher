// Shipped languages, like "pt" or "pt_BR", listed without loading them
const LANGUAGES = require
  .context("../../public/i18n", true, /translation\.json$/, "lazy")
  .keys()
  .map((path) => path.split("/")[1]);

// Map a locale like "pt-BR" to the most precise shipped language
export function pickLanguage(locale) {
  const tag = locale.replace("-", "_");
  const candidates = [tag, tag.substring(0, 2)];
  return candidates.find((lang) => LANGUAGES.includes(lang)) || "en";
}

export async function loadLanguage(lang) {
  try {
    const messages = await import(
      /* webpackChunkName: "lang-[request]" */ `../../public/i18n/${lang}/translation.json`
    );
    return messages;
  } catch (error) {
    console.warn(
      `Cannot import ${lang} language messages, falling back to English.`,
      error
    );

    // fallback to english
    if (lang !== "en") {
      return loadLanguage("en");
    }
  }
}
