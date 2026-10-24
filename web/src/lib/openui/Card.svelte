<script lang="ts">
  import type { Snippet } from 'svelte';
  import * as Card from '#lib/components/ui/card/index.js';
  let { props, renderNode }: { props: { title?: string; children?: unknown }; renderNode: Snippet<[unknown]> } = $props();
</script>

<Card.Root class="shadow-none">
  {#if props.title}<Card.Header><Card.Title>{props.title}</Card.Title></Card.Header>{/if}
  <Card.Content class="space-y-3">
    {#if props.children}{@render renderNode(props.children)}{/if}
  </Card.Content>
</Card.Root>
