<script lang="ts">
  import { onMount, type Component } from "svelte";

  import { pickLanguage } from "./lib/format";
  import { i18n, loadTexts } from "./lib/i18n.svelte";
  import { refreshSession, session } from "./lib/session.svelte";
  import Login from "./pages/Login.svelte";
  import Setup from "./pages/Setup.svelte";
  import Shell from "./pages/Shell.svelte";

  let ready = $state(false);

  /** In the demo on a small screen: a notice first (demo/MobileNotice). */
  let Notice = $state<Component<{ onContinue: () => void }> | null>(null);

  /** Before the account, the language of the browser; then the settings'.
   * With the login off (SOK_AUTH=none), the app opens without an account. */
  async function start() {
    const current = await refreshSession();
    if (current.account || current.logged_in) {
      await loadTexts(current.language);
    } else {
      await loadTexts();
      const browser = pickLanguage(navigator.languages, i18n.languages);
      if (browser && browser !== i18n.language) {
        await loadTexts(browser);
      }
    }
    if (import.meta.env.MODE === "demo") {
      const notice = await import("./demo/MobileNotice.svelte");
      if (notice.needed()) Notice = notice.default;
    }
    ready = true;
  }

  async function loggedIn() {
    const current = await refreshSession();
    await loadTexts(current.language);
  }

  onMount(start);
</script>

{#if ready && session.current}
  {#if Notice}
    <Notice onContinue={() => (Notice = null)} />
  {:else if session.current.logged_in}
    <Shell />
  {:else if !session.current.account}
    <Setup onDone={loggedIn} />
  {:else}
    <Login onDone={loggedIn} />
  {/if}
{/if}
