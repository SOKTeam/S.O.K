<script lang="ts">
  import { onMount } from "svelte";

  import { pickLanguage } from "./lib/format";
  import { i18n, loadTexts } from "./lib/i18n.svelte";
  import { navigate, replace } from "./lib/router.svelte";
  import { refreshSession, session } from "./lib/session.svelte";
  import Login from "./pages/Login.svelte";
  import Setup from "./pages/Setup.svelte";
  import Shell from "./pages/Shell.svelte";

  let ready = $state(false);

  // The step of the first launch assistant, kept for a reload: it stays
  // open after its folders are set, until its last step.
  const STEP_KEY = "sok-setup-step";
  let step = $state(readStep());

  function readStep(): number {
    try {
      return Number(sessionStorage.getItem(STEP_KEY)) || 0;
    } catch {
      return 0;
    }
  }

  $effect(() => {
    try {
      if (step) sessionStorage.setItem(STEP_KEY, String(step));
      else sessionStorage.removeItem(STEP_KEY);
    } catch {
      // Kept for this page only.
    }
  });

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
    ready = true;
  }

  async function loggedIn() {
    const current = await refreshSession();
    await loadTexts(current.language);
  }

  // The page shown: the assistant (without an account, or until a source
  // and a destination are set), the login, or the app.
  const view = $derived.by(() => {
    const current = session.current;
    if (!current) return null;
    if (current.logged_in) return !current.configured || step ? "setup" : "app";
    return current.account ? "login" : "setup";
  });

  // Every address leads to the assistant while it is open.
  $effect(() => {
    if (view !== "setup") return;
    if (!step) step = session.current?.account ? 2 : 1;
    replace("/setup");
  });

  async function setupDone() {
    step = 0;
    await refreshSession();
    navigate("/");
  }

  onMount(start);
</script>

{#if ready && view}
  {#if view === "app"}
    <Shell />
  {:else if view === "setup"}
    <Setup bind:step onDone={setupDone} />
  {:else}
    <Login onDone={loggedIn} />
  {/if}
{/if}
