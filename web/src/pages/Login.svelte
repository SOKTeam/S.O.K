<script lang="ts">
  // The login: the form at the left, the S.O.K cube lit at the right.
  // Nothing of the library before the login.
  import { onMount } from "svelte";

  import Mark from "../components/layout/Mark.svelte";
  import SceneLight from "../components/layout/SceneLight.svelte";
  import Split from "../components/layout/Split.svelte";
  import Cube from "../components/nav/Cube.svelte";
  import { api } from "../lib/api";
  import { errorText } from "../lib/errors";
  import { fillParts } from "../lib/format";
  import { t } from "../lib/i18n.svelte";
  import { setLight } from "../lib/light.svelte";

  let { onDone }: { onDone: () => void } = $props();

  let username = $state("");
  let password = $state("");
  let error = $state("");
  let busy = $state(false);
  let version = $state("");

  onMount(() => {
    setLight("251, 96, 72");
    api<{ version: string }>("/api/health")
      .then((health) => (version = health.version))
      .catch(() => {});
    return () => setLight(null);
  });

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

<SceneLight strength={0.55} />
<div class="relative mx-auto flex h-full max-w-[1760px] flex-col">
  <nav class="flex h-[76px] shrink-0 items-center px-9"><Mark /></nav>
  <main class="min-h-0 flex-1">
    <Split>
      <div class="my-auto w-full max-w-[470px] py-8 lg:ml-[120px]">
        <p class="label mb-2.5">S.O.K Server · {location.hostname}</p>
        <h1 class="m-0 text-[50px] leading-[1.04] font-[650] tracking-[-0.04em]">
          {t("web_login_title", "Log in")}<span class="text-muted">.</span>
        </h1>
        <p class="mt-3 max-w-[420px] text-[15px] leading-[1.45] text-muted">
          {t(
            "web_login_lead",
            "This server sorts the downloads of this machine. Enter your name and your password to go on.",
          )}
        </p>
        <form class="mt-[30px] grid gap-4" onsubmit={submit}>
          <label class="grid gap-[7px]">
            <span class="text-[13px] font-semibold text-muted"
              >{t("web_username", "User name")}</span
            >
            <input
              class="field h-11 text-[15px]"
              bind:value={username}
              autocomplete="username"
              required
            />
          </label>
          <label class="grid gap-[7px]">
            <span class="text-[13px] font-semibold text-muted">{t("web_password", "Password")}</span
            >
            <input
              class={["field h-11 text-[15px]", error && "border-accent"]}
              type="password"
              bind:value={password}
              autocomplete="current-password"
              required
            />
          </label>
          {#if error}
            <p class="-mt-0.5 text-[13.5px] text-caution" role="alert">{error}</p>
          {/if}
          <button class="key key-primary mt-2 h-[46px] w-full" disabled={busy}>
            {t("web_log_in", "Log in")}
          </button>
        </form>
        <p class="mt-[22px] text-[13px] leading-[1.5] text-faint">
          {#each fillParts( t("web_forgot_password", "Forgot the password: restart the server with {reset} and the new one in {password}."), { reset: "SOK_RESET_PASSWORD=1", password: "SOK_PASSWORD" } ) as part, i (i)}{#if part.value}<code
                class="font-mono text-[12.5px] text-muted">{part.text}</code
              >{:else}{part.text}{/if}{/each}
        </p>
      </div>
      {#snippet scene()}
        <div class="my-auto flex flex-col items-center pb-10">
          <div class="text-ink drop-shadow-[0_30px_40px_var(--drop)]"><Cube size={170} /></div>
          <div
            class="mt-[26px] h-[22px] w-[230px] rounded-[50%] bg-[radial-gradient(closest-side,var(--drop),transparent)]"
          ></div>
          <p class="label mt-[34px]">S.O.K Server</p>
          {#if version}
            <p class="mt-1.5 font-mono text-[12.5px] text-faint">
              {t("web_version_n", "version {version}", { version })}
            </p>
          {/if}
        </div>
      {/snippet}
    </Split>
  </main>
</div>
