<script lang="ts">
  import { Chat } from '@ai-sdk/svelte';
  import { ArrowUp, Square } from '@lucide/svelte';
  import { Button } from '#lib/components/ui/button/index.js';
  import { Textarea } from '#lib/components/ui/textarea/index.js';

  const chat = new Chat({
    // Trace transient tool events without adding them to conversation history.
    onData: ({ type, data }) => {
      if (type === 'data-tool-call') console.log('[Chat] Tool call:', data);
      else if (type === 'data-tool-result') {
        console.log('[Chat] Tool result:', data);
        console.info('[Chat] Thinking: waiting for the model to continue.');
      } else if (type === 'data-tool-error') console.error('[Chat] Tool error:', data);
    },
    onError: (error) => {
      console.error('[Chat] Error:', error);
    },

    // Log the raw model text when each response finishes.
    onFinish: ({ message }) => {
      console.log('[Chat] Model output:', message.parts.filter((part) => part.type === 'text').map((part) => part.text).join(''));
    },
  });
  let input = $state('');
  let messagesEnd = $state<HTMLDivElement>();
  const busy = $derived(chat.status === 'submitted' || chat.status === 'streaming');

  function send(text = input) {
    if (!text.trim() || busy) return;

    // Record the user turn and mark the start of the model request.
    console.log('[Chat] User message:', text.trim());
    console.info('[Chat] Thinking: waiting for the model response.');
    input = '';
    chat.clearError();
    void chat.sendMessage({ text: text.trim() });
  }

  $effect(() => {
    void JSON.stringify(chat.messages.at(-1));
    messagesEnd?.scrollIntoView({ behavior: 'instant', block: 'end' });
  });
</script>

<svelte:head>
  <title>Swiss Chat</title>
  <meta name="description" content="Explore Swiss data through natural language." />
</svelte:head>

<div class="flex h-dvh flex-col">
  <main class="flex min-h-0 flex-1 flex-col" class:justify-center={chat.messages.length === 0}>
    {#if chat.messages.length > 0}
      <div class="flex-1 overflow-y-auto">
        <div role="log" aria-label="Conversation" aria-live="polite" class="mx-auto max-w-3xl space-y-8 px-5 py-8">
          {#each chat.messages as message (message.id)}
            {@const text = message.parts.filter((part) => part.type === 'text').map((part) => part.text).join('')}
            {#if message.role === 'user'}
              <div class="flex justify-end"><div class="max-w-[85%] whitespace-pre-wrap break-words rounded-xl bg-muted px-4 py-3 text-[15px] leading-7">{text}</div></div>
            {:else if message.role === 'assistant' && text}
              <div class="min-w-0 whitespace-pre-wrap break-words text-[15px] leading-7">{text}</div>
            {/if}
          {/each}
          {#if chat.status === 'submitted'}<p role="status" class="text-sm text-muted-foreground">Thinking…</p>{/if}
          <div bind:this={messagesEnd}></div>
        </div>
      </div>
    {/if}

    <div class="mx-auto w-full max-w-3xl shrink-0 px-4 pb-4 pt-3 sm:px-5">
      {#if chat.messages.length === 0}
        <span role="img" aria-label="Swiss flag" class="mb-6 block text-center text-4xl">🇨🇭</span>
        <h1 class="mb-8 text-center text-3xl font-medium tracking-tight sm:text-4xl">How can I help?</h1>
      {/if}
      {#if chat.error}<div role="alert" class="mb-3 rounded-xl border border-destructive/20 bg-destructive/5 p-3 text-sm text-destructive">{chat.error.message}<Button variant="ghost" size="sm" onclick={() => { chat.clearError(); void chat.regenerate(); }}>Try again</Button></div>{/if}
      <form class="flex items-end gap-2 rounded-xl bg-neutral-200 p-2" onsubmit={(event) => { event.preventDefault(); send(); }}>
        <Textarea aria-label="Message" placeholder="Message…" bind:value={input} rows={1} class="max-h-40 min-h-10 resize-none border-0 bg-transparent px-2 py-2 text-base shadow-none focus-visible:ring-0" onkeydown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); send(); } }} />
        {#if busy}<Button size="icon-lg" class="h-auto w-10 self-stretch" variant="secondary" aria-label="Stop response" onclick={() => void chat.stop()}><Square class="size-3 fill-current" /></Button>{:else}<Button type="submit" size="icon-lg" class="h-auto w-10 self-stretch" disabled={!input.trim()} aria-label="Send message"><ArrowUp class="size-4" /></Button>{/if}
      </form>
    </div>
  </main>
  <footer class="shrink-0 px-4 pb-4 text-center text-xs text-muted-foreground">
    AI can make mistakes · <a href="https://github.com/xLongLink/askch" class="underline">Open Source</a> · Created by <a href="https://www.linkedin.com/company/longlink" class="underline">LongLink SAGL</a>
  </footer>
</div>
