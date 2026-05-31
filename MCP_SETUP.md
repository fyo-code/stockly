# MCP Configuration Setup

Complete this template with your API keys and configuration details. Once filled, let Claude know and I'll set up the MCP connections in `~/.claude.json`.

---

## 1. GitHub MCP

**Get your API key:**
1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name (e.g., "Claude Code")
4. Select scopes: `repo`, `read:user`, `user:email`
5. Generate and copy the token

**Paste here:**
```
GITHUB_PERSONAL_ACCESS_TOKEN: 
```

---

## 2. Vercel MCP

**Get your API key:**
1. Go to https://vercel.com/account/tokens
2. Click "Create Token"
3. Give it a name (e.g., "Claude Code")
4. Leave scope as default or select "Full Account Access"
5. Copy the token

**Paste here:**
```
VERCEL_API_TOKEN: 
```

---

## 3. Supabase MCP

**Get your credentials:**
1. Go to https://supabase.com/dashboard/projects
2. Select your project
3. Go to Settings → API
4. Copy:
   - **Project URL** (e.g., https://xxxxx.supabase.co)
   - **API Key** (anon or service_role key)

**Paste here:**
```
SUPABASE_PROJECT_REF: 
SUPABASE_API_KEY: 
```

---

## 4. Notion MCP

**Get your API key:**
1. Go to https://www.notion.so/my-integrations
2. Click "Create new integration"
3. Give it a name (e.g., "Claude Code")
4. Copy the "Internal Integration Token"
5. Share your Notion workspace/pages with this integration

**Paste here:**
```
NOTION_API_KEY: 
```

---

## Instructions When Done

Once you've filled in all the API keys above:

1. **Tell me:** "I've filled in the MCP setup template"
2. **I will:** Read your keys and update `~/.claude.json` to enable all MCPs
3. **You'll have:** Full access to GitHub, Vercel, Supabase, and Notion from Claude Code

---

## Notes

- Keep these keys **SECRET** — don't commit this file to git
- Add to `.gitignore` if storing locally: `MCP_SETUP.md`
- The setup is ONE-TIME — once MCPs are active, you won't need this file
- If you skip any service, just leave it blank and I'll skip that MCP
