<script lang="ts">
  import { onMount } from "svelte";

  import NavBar from "../components/nav/NavBar.svelte";
  import { light } from "../lib/light.svelte";
  import { t } from "../lib/i18n.svelte";
  import { pageOf } from "../lib/pages";
  import { router } from "../lib/router.svelte";
  import { refreshRename } from "../lib/renames.svelte";
  import { listen } from "../lib/scan.svelte";
  import { session } from "../lib/session.svelte";
  import Analysis from "./Analysis.svelte";
  import History from "./History.svelte";
  import MediaScreen from "./MediaScreen.svelte";
  import MediaTab from "./MediaTab.svelte";
  import Settings from "./Settings.svelte";

  const page = $derived(pageOf(router.path));

  // The analysis and its progress, live, for every page.
  onMount(() => {
    refreshRename().catch(() => {});
    return listen();
  });
</script>

<!-- The light of the scene, painted by the window behind everything. -->
<div class="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden="true">
  <div
    class="absolute -top-[330px] -right-[280px] size-[1100px] rounded-full transition-[background] duration-500"
    style:background={light.color
      ? `radial-gradient(closest-side, rgba(${light.color}, var(--halo)), transparent 72%)`
      : "none"}
  ></div>
</div>
<div class="relative mx-auto flex h-full max-w-[1760px] flex-col">
  <div class="flex min-h-0 flex-1 flex-col">
    {#if import.meta.env.MODE === "demo"}
      <p class="border-b border-line px-9 py-2 text-[13px] text-muted" role="status">
        {t("web_demo", "Demo: no file is really renamed. Reload the page to start again.")}
        <a class="link ml-1 font-medium" href="/guide/server">
          {t("web_demo_install", "Install S.O.K Server")}
        </a>
        <span class="mt-0.5 block text-xs text-faint">
          {t(
            "web_demo_tmdb",
            "Movie and TV data: TMDB. This product uses the TMDB API but is not endorsed or certified by TMDB.",
          )}
        </span>
      </p>
    {/if}
    {#if session.current?.auth === "none"}
      <p class="border-b border-line px-9 py-2 text-[13px] text-caution" role="status">
        {t(
          "web_auth_off",
          "The login is turned off (SOK_AUTH=none): protect this server with your reverse proxy.",
        )}
      </p>
    {/if}
    <NavBar />
    <main class="min-h-0 flex-1">
      {#if page.path === "/"}
        <Analysis />
      {:else if ["movies", "tv", "music", "books"].includes(page.mediaType ?? "")}
        <MediaScreen {page} />
      {:else}
        <!-- TEMPORARY: the old screens, until each is redrawn. -->
        <div class="h-full overflow-y-auto px-9 pt-2 pb-8">
          {#if page.path === "/settings"}
            <Settings />
          {:else if page.path === "/history"}
            <History />
          {:else if page.mediaType}
            <MediaTab {page} />
          {:else}
            <h1 class="text-2xl font-bold">{t(page.key, page.english)}</h1>
          {/if}
        </div>
      {/if}
    </main>
  </div>
</div>
