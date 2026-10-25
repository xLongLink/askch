<script lang="ts">
  import { Chat } from '@ai-sdk/svelte';
  import { ArrowUp, Square } from '@lucide/svelte';
  import { marked } from 'marked';
  import sanitizeHtml from 'sanitize-html';
  import { onMount } from 'svelte';
  import { Button } from '#lib/components/ui/button/index.js';
  import { Textarea } from '#lib/components/ui/textarea/index.js';

  const chat = new Chat({
    onData: ({ type }) => {
      if (type === 'data-tool-error') console.error('[Chat] Tool call failed.');
    },
    onError: () => {
      console.error('[Chat] Request failed.');
    },
  });
  let input = $state('');
  let messagesEnd = $state<HTMLDivElement>();
  const busy = $derived(chat.status === 'submitted' || chat.status === 'streaming');

  // Use language preferences as a regional hint without requesting location.
  const defaultGreeting = { languages: ['en'], lang: 'en', text: 'Hello! Welcome.' };
  const greetings = [
    { languages: ['de', 'gsw'], lang: 'de-CH', text: 'Grüezi! Willkommen.' },
    { languages: ['fr'], lang: 'fr-CH', text: 'Bonjour ! Bienvenue.' },
    { languages: ['it'], lang: 'it-CH', text: 'Ciao! Benvenuti.' },
    { languages: ['rm'], lang: 'rm-CH', text: 'Allegra! Bainvegni.' },
    defaultGreeting,
  ];
  let greeting = $state(defaultGreeting);

  onMount(() => {
    for (const locale of navigator.languages.length ? navigator.languages : [navigator.language]) {
      const language = locale.toLowerCase().split('-')[0];
      const match = greetings.find((candidate) => candidate.languages.includes(language));
      if (match) {
        greeting = match;
        break;
      }
    }
  });

  function send(text = input) {
    if (!text.trim() || busy) return;

    input = '';
    chat.clearError();
    void chat.sendMessage({ text: text.trim() });
  }

  $effect(() => {
    void chat.messages.at(-1);
    messagesEnd?.scrollIntoView({ behavior: 'instant', block: 'end' });
  });
</script>

<svelte:head>
  <title>Swiss Chat</title>
  <meta name="description" content="Explore Swiss data through natural language." />
</svelte:head>

<div class="flex h-dvh flex-col bg-cover bg-center" style:--overlay-opacity={chat.messages.length === 0 ? '60%' : '83%'} style="background-image: linear-gradient(rgb(253 252 251 / var(--overlay-opacity)), rgb(253 252 251 / var(--overlay-opacity))), url('/mountains.jpg')">
  <main class="flex min-h-0 flex-1 flex-col" class:justify-center={chat.messages.length === 0}>
    {#if chat.messages.length > 0}
      <div class="flex-1 overflow-y-auto">
        <div role="log" aria-label="Conversation" aria-live="polite" class="mx-auto max-w-3xl space-y-8 px-5 py-8">
          {#each chat.messages as message (message.id)}
            {@const text = message.parts.filter((part) => part.type === 'text').map((part) => part.text).join('')}
            {#if message.role === 'user'}
              <div class="flex justify-end"><div class="max-w-[85%] whitespace-pre-wrap break-words rounded-xl bg-muted px-4 py-3 text-[15px] leading-7">{text}</div></div>
            {:else if message.role === 'assistant' && text}
              <div class="markdown min-w-0 break-words text-[15px] leading-7">{@html sanitizeHtml(marked.parse(text, { async: false }))}</div>
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
        <h1 lang={greeting.lang} class="mb-8 text-center text-3xl font-medium tracking-tight sm:text-4xl">{greeting.text}</h1>
      {/if}
      {#if chat.error}<div role="alert" class="mb-3 rounded-xl border border-destructive/20 bg-destructive/5 p-3 text-sm text-destructive">{chat.error.message}<Button variant="ghost" size="sm" onclick={() => { chat.clearError(); void chat.regenerate(); }}>Try again</Button></div>{/if}
      <form class="flex items-end gap-2 rounded-xl bg-neutral-200 p-2" onsubmit={(event) => { event.preventDefault(); send(); }}>
        <Textarea aria-label="Message" placeholder="Message…" bind:value={input} rows={1} class="max-h-40 min-h-10 resize-none border-0 bg-transparent px-2 py-2 text-base shadow-none focus-visible:ring-0" onkeydown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); send(); } }} />
        {#if busy}<Button size="icon-lg" class="h-auto w-10 self-stretch" variant="secondary" aria-label="Stop response" onclick={() => void chat.stop()}><Square class="size-3 fill-current" /></Button>{:else}<Button type="submit" size="icon-lg" class="h-auto w-10 self-stretch" disabled={!input.trim()} aria-label="Send message"><ArrowUp class="size-4" /></Button>{/if}
      </form>
    </div>
  </main>
  <footer class="shrink-0 px-4 pb-4 text-center text-xs text-neutral-600">
    AI can make mistakes · <a href="https://github.com/xLongLink/askch" class="underline">Open Source</a> · Created by <a href="https://www.linkedin.com/company/longlink" class="underline">LongLink SAGL</a>
  </footer>
</div>
