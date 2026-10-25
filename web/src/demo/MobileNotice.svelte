<script module lang="ts">
  const SEEN = "sok-demo-small-screen";

  /** Whether to warn: a small screen, and not yet seen in this tab. */
  export function needed(): boolean {
    if (!matchMedia("(max-width: 767px)").matches) return false;
    try {
      return sessionStorage.getItem(SEEN) !== "1";
    } catch {
      return true;
    }
  }
</script>

<script lang="ts">
  import { t } from "../lib/i18n.svelte";

  // The demo on a phone: a screen of its own, that advises against it. The
  // visitor can still go on; the choice lasts for the tab.
  let { onContinue }: { onContinue: () => void } = $props();

  function goOn() {
    try {
      sessionStorage.setItem(SEEN, "1");
    } catch {
      // Without storage, the screen comes back at the next load.
    }
    onContinue();
  }
</script>

<main class="flex min-h-dvh flex-col px-6 pt-16 pb-[max(2rem,env(safe-area-inset-bottom))]">
  <div class="flex flex-1 flex-col items-center justify-center gap-4 text-center">
    <img src={`${import.meta.env.BASE_URL}favicon.svg`} alt="" class="size-16" />
    <h1 class="text-2xl font-bold">{t("web_demo_mobile_title", "S.O.K Server demo")}</h1>
    <p class="max-w-xs text-base text-muted">
      {t(
        "web_demo_mobile_text",
        "S.O.K Server was not designed for mobile use. We advise against using it on a phone.",
      )}
    </p>
  </div>
  <div class="flex flex-col gap-2">
    <button class="button w-full py-3.5 text-base" onclick={goOn}>
      {t("web_demo_mobile_continue", "Continue anyway")}
    </button>
    <a class="py-3 text-center text-base font-semibold text-accent" href="/">
      {t("web_demo_mobile_back", "Back to the site")}
    </a>
  </div>
</main>
