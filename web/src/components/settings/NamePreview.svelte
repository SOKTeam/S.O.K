<script lang="ts">
  // The live preview of a name: the stand-in of the example file of a type,
  // its path before, the path it would get after (the parts filled by S.O.K
  // in coral), and what the file mode does to the original.
  import { t } from "../../lib/i18n.svelte";
  import { EXAMPLE_COLORS, EXAMPLES, previewPath } from "../../lib/namePreview";
  import { MEDIA_PAGES } from "../../lib/pages";
  import type { FileMode } from "../../lib/settings.svelte";

  let {
    label,
    type,
    model,
    destination,
    source,
    mode,
  }: {
    label: string;
    /** movies, tv, music, books or games. */
    type: string;
    model: string;
    /** The first folder of the type; "" when it has none. */
    destination: string;
    source: string;
    mode: FileMode;
  } = $props();

  const page = $derived(MEDIA_PAGES.find((p) => p.mediaType === type)!);
  const from = $derived(source || "/downloads");
  const after = $derived(
    previewPath(type, model, destination || `/${t(page.key, page.english)}`, t("season", "Season")),
  );
  const colors = $derived(EXAMPLE_COLORS[type]);
  const shape = $derived(type === "music" ? "square" : type === "books" ? "book" : "poster");

  const modeLine = $derived(
    {
      link: t("web_preview_link", "Hard link: the original stays in {folder}.", { folder: from }),
      copy: t("web_preview_copy", "Copy: the original stays in {folder}.", { folder: from }),
      move: t("web_preview_move", "Moved: it leaves {folder}.", { folder: from }),
    }[mode],
  );
</script>

<p class="label mb-[26px] self-stretch">{label}</p>
<div
  class={[
    "relative flex shrink-0 flex-col justify-end overflow-hidden px-[18px] py-4 shadow-[0_30px_60px_var(--drop),inset_0_1px_0_rgb(255_255_255/0.25),inset_0_0_0_1px_rgb(255_255_255/0.1)]",
    shape === "square" && "size-[230px] rounded-xl",
    shape === "poster" && "h-[315px] w-[210px] rounded-xl",
    shape === "book" && "h-[300px] w-[200px] rounded-[4px_10px_10px_4px]",
  ]}
  style:background={`linear-gradient(170deg, ${colors[0]}, ${colors[1]})`}
  aria-hidden="true"
>
  {#if shape === "book"}
    <span class="absolute inset-y-0 left-0 w-3 bg-linear-to-r from-black/30 to-transparent"></span>
  {/if}
  <small class="font-mono text-[10.5px] font-semibold text-white/75">{EXAMPLES[type].year}</small>
  <b class="mt-1 text-[23px] leading-[1.1] font-[650] tracking-[-0.03em] text-white">
    {EXAMPLES[type].title}
  </b>
</div>
<div
  class="-mt-1 h-5 w-[250px] shrink-0 rounded-[50%] bg-[radial-gradient(closest-side,var(--drop),transparent)]"
></div>
<div class="mt-[26px] grid gap-3.5 self-stretch">
  <div>
    <p class="text-[13px] text-muted">{t("web_before", "Before")}</p>
    <p class="mt-1 font-mono text-[13px] leading-[1.45] break-all text-faint">
      {from.replace(/\/+$/, "")}/{EXAMPLES[type].before}
    </p>
  </div>
  <div>
    <p class="text-[13px] text-muted">{t("web_after", "After")}</p>
    <p class="mt-1 font-mono text-[13px] leading-[1.45] break-all text-ink">
      {#if after}
        {#each after as piece, i (i)}<span class={piece.filled ? "text-accent-text" : ""}
            >{piece.text}</span
          >{/each}
      {:else}
        <span class="font-sans text-faint">{t("web_preview_none", "No name with this model.")}</span
        >
      {/if}
    </p>
  </div>
  <p class="text-[13px] leading-[1.45] text-muted">{modeLine}</p>
</div>
