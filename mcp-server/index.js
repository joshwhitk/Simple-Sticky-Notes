#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const REPO_ROOT = resolve(__dirname, '..');
const PYTHON = process.env.SIMPLE_STICKY_NOTES_PYTHON || 'python';

const TOOLS = [
  {
    name: 'get_sticky_notes_status',
    description: 'Report the active storage root, detected Obsidian vault, note counts, and whether the desktop tray app is running.',
    inputSchema: {
      type: 'object',
      properties: {}
    }
  },
  {
    name: 'list_sticky_notes',
    description: 'List sticky notes from the configured Obsidian-backed storage. Optionally limit to notes marked open.',
    inputSchema: {
      type: 'object',
      properties: {
        open_only: { type: 'boolean', description: 'Only return notes marked open.' }
      }
    }
  },
  {
    name: 'search_sticky_notes',
    description: 'Search sticky notes by title, body, or markdown filename.',
    inputSchema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Search text. Empty returns recent notes.' },
        limit: { type: 'integer', description: 'Maximum number of notes to return.' }
      }
    }
  },
  {
    name: 'notes_changed_since',
    description: 'List sticky notes updated after a given UTC ISO timestamp.',
    inputSchema: {
      type: 'object',
      properties: {
        since: { type: 'string', description: 'UTC ISO timestamp such as 2026-04-27T10:30:00+00:00.' },
        limit: { type: 'integer', description: 'Maximum number of notes to return.' }
      },
      required: ['since']
    }
  },
  {
    name: 'get_sticky_note',
    description: 'Fetch one sticky note by note id.',
    inputSchema: {
      type: 'object',
      properties: {
        note_id: { type: 'string', description: 'Sticky note id.' }
      },
      required: ['note_id']
    }
  },
  {
    name: 'create_sticky_note',
    description: 'Create a sticky note in storage. This does not force a live desktop window to appear in an already-running app.',
    inputSchema: {
      type: 'object',
      properties: {
        body: { type: 'string', description: 'Markdown body for the note.' },
        title: { type: 'string', description: 'Optional title seed. File naming still follows app rules.' },
        bg_color: { type: 'string', description: 'Hex color like #ffd54f.' },
        is_open: { type: 'boolean', description: 'Whether the note should be marked open in metadata.' },
        x: { type: 'integer' },
        y: { type: 'integer' },
        width: { type: 'integer' },
        height: { type: 'integer' }
      },
      required: ['body']
    }
  },
  {
    name: 'create_visible_sticky_note',
    description: 'Create a sticky note in storage and ask the running desktop app to show it immediately if the tray instance is running.',
    inputSchema: {
      type: 'object',
      properties: {
        body: { type: 'string', description: 'Markdown body for the note.' },
        title: { type: 'string', description: 'Optional title seed. File naming still follows app rules.' },
        bg_color: { type: 'string', description: 'Hex color like #ffd54f.' },
        x: { type: 'integer' },
        y: { type: 'integer' }
      },
      required: ['body']
    }
  },
  {
    name: 'edit_sticky_note',
    description: 'Replace or modify a sticky note body and selected metadata fields.',
    inputSchema: {
      type: 'object',
      properties: {
        note_id: { type: 'string' },
        body: { type: 'string', description: 'Full replacement body.' },
        append_text: { type: 'string', description: 'Text to append.' },
        prepend_text: { type: 'string', description: 'Text to prepend.' },
        bg_color: { type: 'string' },
        is_open: { type: 'boolean' }
      },
      required: ['note_id']
    }
  },
  {
    name: 'show_sticky_note',
    description: 'Tell the running desktop app to show and focus an existing sticky note window.',
    inputSchema: {
      type: 'object',
      properties: {
        note_id: { type: 'string' }
      },
      required: ['note_id']
    }
  },
  {
    name: 'move_resize_sticky_note',
    description: 'Update stored note geometry and tell the running app to move and resize that note window.',
    inputSchema: {
      type: 'object',
      properties: {
        note_id: { type: 'string' },
        x: { type: 'integer' },
        y: { type: 'integer' },
        width: { type: 'integer' },
        height: { type: 'integer' },
        focus: { type: 'boolean', description: 'Focus the note after moving it.' }
      },
      required: ['note_id', 'x', 'y', 'width', 'height']
    }
  },
  {
    name: 'tidy_sticky_notes',
    description: 'Ask the running desktop app to move and resize all open sticky notes onto the main screen.',
    inputSchema: {
      type: 'object',
      properties: {}
    }
  },
  {
    name: 'hide_sticky_note',
    description: 'Mark a sticky note hidden without deleting it.',
    inputSchema: {
      type: 'object',
      properties: {
        note_id: { type: 'string' }
      },
      required: ['note_id']
    }
  },
  {
    name: 'reopen_sticky_note',
    description: 'Mark a sticky note open in metadata.',
    inputSchema: {
      type: 'object',
      properties: {
        note_id: { type: 'string' }
      },
      required: ['note_id']
    }
  },
  {
    name: 'open_sticky_note_in_obsidian',
    description: 'Open the sticky note markdown file in Obsidian using the vault-aware URI when possible.',
    inputSchema: {
      type: 'object',
      properties: {
        note_id: { type: 'string' }
      },
      required: ['note_id']
    }
  },
  {
    name: 'reveal_sticky_note_in_explorer',
    description: 'Open the containing folder for the sticky note markdown file in Windows Explorer.',
    inputSchema: {
      type: 'object',
      properties: {
        note_id: { type: 'string' }
      },
      required: ['note_id']
    }
  },
  {
    name: 'delete_sticky_note',
    description: 'Delete a sticky note markdown file and metadata.',
    inputSchema: {
      type: 'object',
      properties: {
        note_id: { type: 'string' }
      },
      required: ['note_id']
    }
  }
];

const COMMAND_BY_TOOL = {
  get_sticky_notes_status: 'get-status',
  list_sticky_notes: 'list-notes',
  search_sticky_notes: 'search-notes',
  notes_changed_since: 'notes-changed-since',
  get_sticky_note: 'get-note',
  create_sticky_note: 'create-note',
  create_visible_sticky_note: 'create-visible-note',
  edit_sticky_note: 'edit-note',
  show_sticky_note: 'show-note-window',
  move_resize_sticky_note: 'move-resize-note',
  tidy_sticky_notes: 'tidy-notes',
  hide_sticky_note: 'hide-note',
  reopen_sticky_note: 'reopen-note',
  open_sticky_note_in_obsidian: 'open-note-in-obsidian',
  reveal_sticky_note_in_explorer: 'reveal-note-in-explorer',
  delete_sticky_note: 'delete-note'
};

function callPython(command, args) {
  const payload = JSON.stringify(args ?? {});
  const result = spawnSync(
    PYTHON,
    ['-m', 'simple_sticky_notes.service_api', command, payload],
    {
      cwd: REPO_ROOT,
      encoding: 'utf8',
      windowsHide: true,   // prevent CMD window from stealing focus on Windows
    }
  );
  if (result.status !== 0) {
    const message = (result.stderr || result.stdout || `python exited ${result.status}`).trim();
    throw new Error(message);
  }
  return JSON.parse(result.stdout);
}

async function main() {
  const server = new Server(
    { name: 'simple-sticky-notes', version: '1.0.0' },
    { capabilities: { tools: {} } }
  );

  server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: TOOLS }));

  server.setRequestHandler(CallToolRequestSchema, async request => {
    const toolName = request.params.name;
    const command = COMMAND_BY_TOOL[toolName];
    if (!command) {
      return { content: [{ type: 'text', text: JSON.stringify({ error: `unknown tool: ${toolName}` }) }] };
    }
    const result = callPython(command, request.params.arguments ?? {});
    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
  });

  const transport = new StdioServerTransport();
  await server.connect(transport);
}

const isEntry = process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, '/').split('/').pop());
if (isEntry) {
  main().catch(error => {
    console.error('simple-sticky-notes MCP server crashed:', error);
    process.exit(1);
  });
}
