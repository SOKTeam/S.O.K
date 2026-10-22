<script lang="ts">
  import AuthCard from "../components/AuthCard.svelte";
  import { api } from "../lib/api";
  import { errorText } from "../lib/errors";
  import { i18n, t } from "../lib/i18n.svelte";

  let { onDone }: { onDone: () => void } = $props();

  let username = $state("");
  let password = $state("");
  let confirm = $state("");
  let error = $state("");
  let busy = $state(false);

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    if (password !== confirm) {
      error = t("web_error_password_mismatch", "The two passwords are not the same.");
      return;
    }
    busy = true;
    error = "";
    try {
      // The language of the page, the browser's, becomes the one of the settings.
      await api("/api/setup", {
        method: "POST",
        body: { username, password, language: i18n.language },
      });
      onDone();
    } catch (exc) {
      error = errorText(exc);
    } finally {
      busy = false;
    }
  }
</script>

<AuthCard
  title={t("web_setup_title", "Welcome")}
  text={t("web_setup_text", "Create the account that protects this server.")}
>
  <form class="flex flex-col gap-4" onsubmit={submit}>
    <label class="flex flex-col gap-1.5 text-sm font-semibold">
      {t("web_username", "User name")}
      <input class="field" bind:value={username} autocomplete="username" required />
    </label>
    <label class="flex flex-col gap-1.5 text-sm font-semibold">
      {t("web_password", "Password")}
      <input
        class="field"
        type="password"
        bind:value={password}
        autocomplete="new-password"
        minlength="8"
        required
      />
    </label>
    <label class="flex flex-col gap-1.5 text-sm font-semibold">
      {t("web_password_confirm", "Confirm the password")}
      <input
        class="field"
        type="password"
        bind:value={confirm}
        autocomplete="new-password"
        required
      />
    </label>
    {#if error}
      <p class="text-sm text-error" role="alert">{error}</p>
    {/if}
    <button class="button mt-2" disabled={busy}>
      {t("web_create_account", "Create the account")}
    </button>
  </form>
</AuthCard>
