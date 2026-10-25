<script lang="ts">
  import AuthCard from "../components/AuthCard.svelte";
  import { api } from "../lib/api";
  import { errorText } from "../lib/errors";
  import { t } from "../lib/i18n.svelte";

  let { onDone }: { onDone: () => void } = $props();

  let username = $state("");
  let password = $state("");
  let error = $state("");
  let busy = $state(false);

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    busy = true;
    error = "";
    try {
      await api("/api/login", { method: "POST", body: { username, password } });
      onDone();
    } catch (exc) {
      error = errorText(exc);
      password = "";
    } finally {
      busy = false;
    }
  }
</script>

<AuthCard title={t("web_log_in", "Log in")}>
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
        autocomplete="current-password"
        required
      />
    </label>
    {#if error}
      <p class="text-sm text-error" role="alert">{error}</p>
    {/if}
    <button class="button mt-2" disabled={busy}>{t("web_log_in", "Log in")}</button>
  </form>
</AuthCard>
