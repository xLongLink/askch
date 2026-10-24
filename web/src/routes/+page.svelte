<script lang="ts">
  import { Chat } from '@ai-sdk/svelte';
  import { Renderer, BuiltinActionType, type ActionEvent } from '@openuidev/svelte-lang';
  import { ArrowUp, Square } from '@lucide/svelte';
  import { Button } from '#lib/components/ui/button/index.js';
  import { Textarea } from '#lib/components/ui/textarea/index.js';
  import { library } from '#lib/library.js';

  const chat = new Chat({});
  let input = $state('');
  let messagesEnd = $state<HTMLDivElement>();
  const busy = $derived(chat.status === 'submitted' || chat.status === 'streaming');

  function send(text = input) {
    if (!text.trim() || busy) return;
    input = '';
    chat.clearError();
    void chat.sendMessage({ text: text.trim() });
  }

  function onAction(event: ActionEvent) {
    if (event.type === BuiltinActionType.ContinueConversation && event.humanFriendlyMessage) send(event.humanFriendlyMessage);
  }

  $effect(() => {
    void JSON.stringify(chat.messages.at(-1));
    messagesEnd?.scrollIntoView({ behavior: 'instant', block: 'end' });
  });
</script>

<svelte:head>
  <title>Swiss Chat</title>
  <meta name="description" content="A simple, private-session chatbot powered by OpenUI." />
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
              <div class="min-w-0"><Renderer response={text} {library} isStreaming={busy && message.id === chat.messages.at(-1)?.id} {onAction} /></div>
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
      <form class="flex items-end gap-2 rounded-xl p-2" onsubmit={(event) => { event.preventDefault(); send(); }}>
        <Textarea aria-label="Message" placeholder="Message…" bind:value={input} rows={1} class="max-h-40 min-h-10 resize-none border-0 bg-transparent px-2 py-2 text-base shadow-none focus-visible:ring-0" onkeydown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); send(); } }} />
        {#if busy}<Button size="icon-lg" class="h-auto w-10 self-stretch" variant="secondary" aria-label="Stop response" onclick={() => void chat.stop()}><Square class="size-3 fill-current" /></Button>{:else}<Button type="submit" size="icon-lg" class="h-auto w-10 self-stretch" disabled={!input.trim()} aria-label="Send message"><ArrowUp class="size-4" /></Button>{/if}
      </form>
    </div>
  </main>
  <footer class="shrink-0 px-4 pb-4 text-center text-xs text-muted-foreground">
    AI can make mistakes · <a href="https://github.com/xLongLink/askch" class="underline">Open Source</a> · Created by <a href="https://www.linkedin.com/company/longlink" class="underline">LongLink SAGL</a>
  </footer>
</div>
