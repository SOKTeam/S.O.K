<script lang="ts">
  // The typographic navigation of the art direction, as in the desktop app:
  // the cube and "S.O.K" (the Analysis, home), a word per media type with the
  // files waiting in superscript, then History, Settings and Log out.
  import Icon from "../Icon.svelte";
  import Cube from "./Cube.svelte";
  import { t } from "../../lib/i18n.svelte";
  import { MEDIA_PAGES, OTHER_PAGES } from "../../lib/pages";
  import { follow, href, router } from "../../lib/router.svelte";
  import { analysis } from "../../lib/scan.svelte";
  import { logOut, session } from "../../lib/session.svelte";

  const ICON: Record<string, string> = { "/history": "nav-history", "/settings": "nav-settings" };

  function current(path: string): boolean {
    return router.path === path || router.path.startsWith(`${path}/`);
  }
</script>

<nav
  class="flex h-[76px] shrink-0 items-center px-9"
  aria-label={t("web_navigation", "Navigation")}
>
  <a
    href={href("/")}
    onclick={follow}
    aria-current={router.path === "/" ? "page" : undefined}
    class={[
      "mr-11 flex items-center gap-2 text-[17px] font-bold",
      router.path === "/" ? "text-ink" : "text-ink hover:text-muted",
    ]}
  >
    <Cube />
    S.O.K
  </a>
  {#each MEDIA_PAGES as page (page.path)}
    {@const on = current(page.path)}
    {@const waiting = analysis.summary?.counts[page.mediaType!]?.total ?? 0}
    <a
      href={href(page.path)}
      onclick={follow}
      aria-current={on ? "page" : undefined}
      class={[
        "mr-[30px] text-[26px] leading-[30px] font-semibold tracking-[-0.035em]",
        on ? "text-ink" : "text-faint hover:text-muted",
      ]}
    >
      {t(page.key, page.english)}{#if waiting}<sup
          class={[
            "ml-[3px] align-[14px] font-mono text-[11px] font-medium tracking-normal",
            on ? "text-accent-text" : "text-faint",
          ]}>{waiting}</sup
        >{/if}
    </a>
  {/each}
  <div class="ml-auto flex items-center gap-1.5">
    {#each OTHER_PAGES as page (page.path)}
      {@const on = current(page.path)}
      <a
        href={href(page.path)}
        onclick={follow}
        aria-current={on ? "page" : undefined}
        title={t(page.key, page.english)}
        aria-label={t(page.key, page.english)}
        class={[
          "flex size-9 items-center justify-center rounded-[10px]",
          on
            ? "bg-raised text-ink shadow-[inset_0_1px_0_var(--color-hi)]"
            : "text-faint hover:bg-raised hover:text-ink",
        ]}
      >
        <Icon name={ICON[page.path]} class="size-5" />
      </a>
    {/each}
    {#if session.current?.auth === "login"}
      <button
        type="button"
        onclick={logOut}
        title={t("web_log_out", "Log out")}
        aria-label={t("web_log_out", "Log out")}
        class="flex size-9 cursor-pointer items-center justify-center rounded-[10px] text-faint hover:bg-raised hover:text-ink"
      >
        <Icon name="nav-logout" class="size-5" />
      </button>
    {/if}
  </div>
</nav>
