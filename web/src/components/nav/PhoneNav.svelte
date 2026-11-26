<script lang="ts">
  // The navigation of a phone (menu D of the narrow screens mockup): the
  // cube, the word of the page and a thin arrow are one toggle; it opens a
  // full-screen menu (every screen with its count, then History, Settings
  // and Log out), the arrow turns up, and the same place closes it.
  import Icon from "../Icon.svelte";
  import Cube from "./Cube.svelte";
  import { t } from "../../lib/i18n.svelte";
  import { ANALYSIS, MEDIA_PAGES, OTHER_PAGES, pageOf } from "../../lib/pages";
  import { follow, href, router } from "../../lib/router.svelte";
  import { analysis } from "../../lib/scan.svelte";
  import { logOut, session } from "../../lib/session.svelte";

  const ICON: Record<string, string> = { "/history": "nav-history", "/settings": "nav-settings" };

  let open = $state(false);

  const page = $derived(pageOf(router.path));
  const countOf = (mediaType?: string) =>
    mediaType
      ? (analysis.summary?.counts[mediaType]?.total ?? 0)
      : MEDIA_PAGES.reduce(
          (sum, p) => sum + (analysis.summary?.counts[p.mediaType!]?.total ?? 0),
          0,
        );
  const current = $derived(page.path === "/" || page.mediaType ? countOf(page.mediaType) : 0);

  // A page chosen closes the menu.
  $effect(() => {
    void router.path;
    open = false;
  });

  $effect(() => {
    if (!open) return;
    const leave = (event: KeyboardEvent) => event.key === "Escape" && (open = false);
    window.addEventListener("keydown", leave);
    return () => window.removeEventListener("keydown", leave);
  });
</script>

<div class={open ? "fixed inset-0 z-50 flex flex-col bg-bg" : "relative"}>
  <div class="flex h-[52px] shrink-0 items-center px-5">
    <button
      type="button"
      class="flex cursor-pointer items-center gap-2.5 text-ink"
      aria-label={t("web_menu", "Menu")}
      aria-expanded={open}
      onclick={() => (open = !open)}
    >
      <Cube size={24} />
      <span class="text-[24px] font-semibold tracking-[-0.03em]">
        {t(page.key, page.english)}{#if current}<sup
            class="ml-0.5 align-[12px] font-mono text-[10.5px] font-medium tracking-normal text-accent-text"
            >{current}</sup
          >{/if}
      </span>
      <svg
        class={[
          "-ml-1.5 translate-y-px transition-transform duration-200",
          open ? "rotate-180 text-ink" : "text-muted",
        ]}
        width="14"
        height="14"
        viewBox="0 0 14 14"
        fill="none"
        stroke="currentColor"
        stroke-width="1.6"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"><path d="M3 5.25 7 9.25l4-4" /></svg
      >
    </button>
  </div>

  {#if open}
    <nav
      class="flex min-h-0 flex-1 flex-col overflow-y-auto px-5 pb-[max(34px,env(safe-area-inset-bottom))]"
      aria-label={t("web_navigation", "Navigation")}
    >
      <div class="mt-6 grid gap-1">
        {#each [ANALYSIS, ...MEDIA_PAGES] as item (item.path)}
          {@const on = page.path === item.path}
          {@const n = countOf(item.mediaType)}
          <a
            href={href(item.path)}
            onclick={follow}
            aria-current={on ? "page" : undefined}
            class={[
              "flex items-baseline justify-between py-0.5 text-[40px] leading-[1.15] font-[650] tracking-[-0.045em]",
              on ? "text-ink" : "text-faint",
            ]}
          >
            <span>
              {t(item.key, item.english)}{#if on}<span
                  class="ml-2.5 inline-block size-2 -translate-y-3.5 rounded-full bg-accent"
                ></span>{/if}
            </span>
            <small
              class={[
                "font-mono text-[14px] font-medium tracking-normal",
                on ? "text-accent-text" : "text-faint",
              ]}
            >
              {n
                ? item.mediaType
                  ? n
                  : t("web_menu_waiting", "{n} to sort", { n })
                : t("web_menu_nothing", "nothing")}
            </small>
          </a>
        {/each}
      </div>
      <div class="mt-auto grid pt-8">
        {#each OTHER_PAGES as item (item.path)}
          <a
            href={href(item.path)}
            onclick={follow}
            class="flex h-[50px] items-center gap-3 border-t border-line text-[16px] font-medium text-muted"
          >
            <Icon name={ICON[item.path]} class="size-5 text-faint" />
            {t(item.key, item.english)}
          </a>
        {/each}
        {#if session.current?.auth === "login"}
          <button
            type="button"
            class="flex h-[50px] cursor-pointer items-center gap-3 border-t border-line text-left text-[16px] font-medium text-muted"
            onclick={logOut}
          >
            <Icon name="nav-logout" class="size-5 text-faint" />
            {t("web_log_out", "Log out")}
            <span class="ml-auto text-[13px] font-normal text-faint"
              >{session.current.username}</span
            >
          </button>
        {/if}
      </div>
    </nav>
  {/if}
</div>
