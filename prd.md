As a business owner, I am **not satisfied** with the previous scope. It was too "linear." It treated business like a simple checklist (Task A $\to$ Task B).

Real business is **chaotic, interconnected, and strategic**. A true "Business Partner" isn't just a chatbot that waits for you to speak; it's a **Multi-Agent Swarm** that is constantly thinking about your Money, your Reach, and your Code, even while you sleep.

To solve the actual problem—*running a one-person business without burning out*—we need to upgrade the architecture from "Task Runners" to a **Role-Based Swarm**.

Here is the **Business-First Architecture** (Revised for High-Value Outcomes).

***

### 1. The "Boardroom" Architecture (Multi-Agent Swarm)
Instead of one generic "Agent," we build a **Swarm of Specialist Agents**. Each has a specific "Personality" (System Prompt) and distinct Tools. They talk to each other before they talk to you.

#### **The Agents (Your C-Suite)**
1.  **The CMO (Marketing Swarm):**
    *   *Goal:* Fill the pipeline.
    *   *Workflow:* Not just "write a post." It monitors trends.
    *   *Action:*
        *   **Trend Watcher:** Scrapes Twitter/HackerNews for "trending dev topics."
        *   **Strategist:** Decides "We need a video on 'LangGraph vs CrewAI'."
        *   **Creator:** Generates the **YouTube Script**, **Thumbnail concept**, **Title options**, and a repurposed **LinkedIn Carousel** text.
2.  **The CRO (Sales & Leads):**
    *   *Goal:* Close deals.
    *   *Action:* Monitors HubSpot. If a lead is stuck, it doesn't just alert you; it *investigates*. "Why is Acme Corp stuck? Let me check their recent news. Oh, they just raised Series B. I'll draft a congratulatory email to unfreeze the deal."
3.  **The CFO (Finance & Ops):**
    *   *Goal:* Cash flow.
    *   *Action:* Watches invoices. "Invoice #302 is 5 days late. I've drafted a polite reminder. Send?"
4.  **The CTO (DevOps - *Existing*):**
    *   *Goal:* Ship code.
    *   *Action:* Handles the "Pocket Architect" PR workflow we defined.

***

### 2. The "Deep Content" Workflow (The Problem Solver)
*Problem:* Generic AI content sucks.
*Solution:* **The "Journalist" Pipeline.**

We don't paste a URL. We give a **topic**.
1.  **Research Phase (Tavily):** The Agent searches for *contrarian views*, *hard data*, and *specific examples*. It ignores generic SEO bloat.
2.  **Structure Phase:** It outlines the content based on proven viral frameworks (e.g., "Hook, Retain, Reward" for YouTube).
3.  **Drafting Phase:**
    *   **YouTube:** Generates specific visual cues ("Cut to screen recording of VS Code") + Script.
    *   **Blog:** writes a 1,500-word technical deep dive with code snippets.
    *   **LinkedIn:** Extracts 3 "Hot Takes" for short-form text.
4.  **Review Phase:** A second "Critic Agent" reads it. "This sounds too robotic. Add more personal anecdotes." (Self-Correction).

***

### 3. The "Proactive" Layer (The Game Changer)
This is what separates a tool from a partner.

**The "Morning Board Meeting" (Daily Notification)**
Instead of a list of tasks, you wake up to a **Strategic Briefing**:

> **Good Morning, Boss.**
>
> *   **Finance:** Invoice #102 ($5k) is overdue. *Action: Reminder Drafted.*
> *   **Sales:** 2 New Leads. One looks high-value (Series B funded). *Action: Research Report Ready.*
> *   **Marketing:** "Devin AI" is trending on X. *Action: I wrote a reaction script comparing it to your AutoAdmin project.*
> *   **Dev:** PR #45 passed tests. *Action: Merge?*
>
> **What should we execute?**

***

### 4. How we Achieve this Technologically (Free Tier Swarm)

To run a **Swarm** without paying for massive compute, we use **LangGraph's Hierarchical State**.

*   **The Orchestrator (GitHub Action):** The "CEO" Node. It runs daily.
*   **The State:** A shared JSON object passed between agents.
    ```json
    {
      "business_context": "Freelance Dev Agency",
      "current_trends": ["AI Agents", "Supabase"],
      "finance_alert": true,
      "marketing_queue": []
    }
    ```
*   **The Execution:**
    1.  **Step 1:** The **Marketing Agent** runs. Checks trends. Updates `marketing_queue`.
    2.  **Step 2:** The **Sales Agent** runs. Checks HubSpot. Updates `sales_alerts`.
    3.  **Step 3:** The **Orchestrator** compiles the "Morning Briefing" from these updates.
    4.  **Step 4:** Pushes the briefing to **Supabase**.
    5.  **Step 5:** Your **Expo App** triggers a Push Notification.

### 5. Satisfaction Check
**Now** I am satisfied.

*   **Problem:** You are overwhelmed and reactive.
*   **Solution:** A system that is **proactive**. It filters the noise, creates the content assets for you (Deep Research), watches your money (CFO), and writes the boilerplate code (CTO).

This transforms the app from a "Task Manager" into a **Business Operation System** that runs in the background, only asking for your executive approval. This is the "10x" vision.


This is the final piece of the puzzle. You want a **"Holistic CTO"**, not just a "Coder."

This agent doesn't just look at *files*; it looks at the **Project Graph**. It understands that changing the "Pricing UI" affects "Conversion Rate" (Business) and "API Latency" (Performance).

To achieve this "Shared Memory" where all agents (Marketing, Finance, CTO) see the same picture, we need a **Knowledge Graph**.

Here is the **Finalized Architecture Upgrade** for the "Graph Memory" system.

***

### 1. The Brain: Shared Graph Memory (GraphRAG)
Instead of just storing files or text, we store **relationships** in a Knowledge Graph.
*   *Constraint:* Neo4j is expensive/heavy for Free Tier.
*   *Solution:* **Supabase (Postgres) as a Graph Database**.
    *   We use a simple `edges` table: `(source_id, target_id, relationship_type)`.
    *   This allows "GraphRAG" without paying for a dedicated Graph DB.

**What the Graph Stores:**
*   `Feature: "Dark Mode"` -- *impacts* --> `Metric: "User Retention"`
*   `File: "auth.ts"` -- *implements* --> `BusinessRule: "Only paid users can export"`
*   `Trend: "AI Agents"` -- *suggests* --> `Content: "Blog Post on LangGraph"`

### 2. The "GitHub Projects" Agent (The Product Manager)
This agent lives above the code. It manages the **GitHub Project Board** (Kanban).

*   **Role:** The Product Owner / Technical Lead.
*   **Trigger:** Daily Scan or Manual "Review Project".
*   **The Logic (GraphRAG):**
    1.  **Cost Efficiency Review:**
        *   *Query:* "Show me features using 'OpenAI API'."
        *   *Graph:* Finds `Feature: Auto-Reply` -> `Dependency: OpenAI`.
        *   *Analysis:* "We are spending $5/mo here. Can we switch to Llama 3 (Free)?"
        *   *Action:* Creates a Ticket: "Refactor Auto-Reply to use Groq."
    2.  **Scoped Features Decision:**
        *   *Query:* "User wants 'Video Editing'."
        *   *Graph:* Checks `Project Scope`. Result: "Out of bounds."
        *   *Action:* Replies: "Rejecting feature. Low ROI. Conflicts with 'Text-First' strategy."
    3.  **Performance/UI/UX Review:**
        *   *Trigger:* New PR created.
        *   *Check:* Does this UI change match our "Cyberpunk Design System" node in the Graph?
        *   *Action:* Comments on PR: "This button uses `blue-500`. Our design system uses `#66FCF1`."

### 3. The "Shared Memory" Implementation (Supabase)
All agents (CMO, CFO, CTO) read/write to this shared brain.

**Table Schema:**
```sql
-- The Nodes (Concepts, Files, Metrics, Trends)
create table nodes (
  id uuid primary key,
  type text, -- 'feature', 'file', 'metric', 'business_rule'
  content text,
  embedding vector(1536) -- For Semantic Search (RAG)
);

-- The Edges (Relationships)
create table edges (
  source_id uuid references nodes(id),
  target_id uuid references nodes(id),
  relation text -- 'impacts', 'depends_on', 'implements'
);
```

**Workflow Example:**
1.  **Marketing Agent** sees a trend "Dark Mode is popular."
    *   *Writes:* `Node("Trend: Dark Mode")` linked to `Node("User Request")`.
2.  **GitHub Project Agent** sees this new node.
    *   *Queries:* "Do we have Dark Mode?" -> Graph says No.
    *   *Decides:* "High impact, Low cost."
    *   *Action:* Creates GitHub Issue: "Implement Dark Mode."
3.  **CTO Agent** picks up the issue.
    *   *Writes Code.*
    *   *Updates Graph:* `File("theme.ts")` -- *implements* --> `Feature("Dark Mode")`.

***

### 4. Revised PRD: The "Swarm" Architecture

**1. The Shared Brain (Supabase Graph)**
*   The single source of truth. Connects Business Goals ("Increase Revenue") to Code ("Checkout.tsx").
*   Powered by **pgvector** for semantic retrieval ("Find code related to Revenue").

**2. The Swarm Agents**
*   **Product Agent (GitHub Projects):** Manages the backlog. Prioritizes features based on ROI nodes in the Graph.
*   **CTO Agent (Code):** Implements tickets. Updates the Graph with technical details.
*   **Review Agent (QA):** Checks PRs against "UX Guidelines" nodes in the Graph.
*   **Business Agent (Strategy):** Injects market trends into the Graph to influence the Product Agent.

**3. The Workflow**
*   **Cycle:** Strategy Agent (Trends) -> Product Agent (Tickets) -> CTO Agent (Code) -> Review Agent (Quality).

### 5. Updated Code Snippet: Simple GraphRAG in Supabase

*File: `agents/lib/graph_memory.ts`*
```typescript
import { createClient } from '@supabase/supabase-js';
import { OpenAI } from 'openai';

// Insert a new concept into Shared Memory
export async function addMemory(content: string, type: string, relatedNodeIds: string[]) {
  const embedding = await getEmbedding(content); // OpenAI/Groq embedding
  
  // 1. Create Node
  const { data: node } = await supabase.from('nodes').insert({
    type,
    content,
    embedding
  }).select().single();

  // 2. Create Edges (Relationships)
  const edges = relatedNodeIds.map(targetId => ({
    source_id: node.id,
    target_id: targetId,
    relation: 'related_to'
  }));
  
  await supabase.from('edges').insert(edges);
}

// "Think" using the Graph (GraphRAG)
export async function queryGraph(question: string) {
  const queryEmbedding = await getEmbedding(question);
  
  // 1. Find relevant nodes (Vector Search)
  const { data: nodes } = await supabase.rpc('match_nodes', { 
    query_embedding: queryEmbedding, 
    match_threshold: 0.7 
  });

  // 2. Expand context (Get neighbors in the Graph)
  const context = [];
  for (const node of nodes) {
    const { data: neighbors } = await supabase
      .from('edges')
      .select('target_id(content, type), relation')
      .eq('source_id', node.id);
      
    context.push(`Node: ${node.content} (${node.type})`);
    context.push(...neighbors.map(n => `  --[${n.relation}]--> ${n.target_id.content}`));
  }

  return context.join('\n');
}
```

**Are you satisfied?**
This architecture turns your "AutoAdmin" into a **Self-Organizing Business**.
*   It doesn't just code; it *understands* why it is coding.
*   It doesn't just research; it *connects* research to your product roadmap.
*   It creates a living "Knowledge Graph" of your entire company, accessible by every agent.

This is the final, 10x, vertical, agentic system. You have the blueprint. Time to build.






This is the **Final Master Construction File**. It integrates the **Deep Agents** framework, the **Graph Memory**, and the **Free Tier Swarm** architecture into a single executable blueprint.

Save this as `AUTOADMIN_MASTER_PLAN.md` and provide it to your AI coding assistant.

***

# Project: AutoAdmin (The Vertical Agentic Business Partner)

## 1. Product Requirements Document (PRD)

### **Vision**
A text-first, mobile "CEO-in-a-Box" that runs a proactive Multi-Agent Swarm. It acts as a **Vertical Business Partner** (Strategy, Marketing, Finance) and a **Pocket Architect** (DevOps, Coding). It leverages "Deep Agents" for hierarchical planning and "Shared Graph Memory" for context awareness, running entirely on free-tier infrastructure.

### **Core Features**
1.  **The Swarm (Deep Agents Architecture):**
    *   **Main Agent (The CEO):** Orchestrates tasks, manages the "Virtual File System," and delegates to sub-agents.
    *   **Strategy Sub-Agent (The CMO/CFO):** Performs deep research (Tavily), monitors trends, and analyzes finance.
    *   **DevOps Sub-Agent (The CTO):** Manages GitHub Projects, writes code on new branches, and opens PRs.
2.  **Shared Graph Memory (The Brain):**
    *   All agents read/write to a Supabase Graph (Nodes/Edges).
    *   *Example:* Marketing writes "Trend: Dark Mode." DevOps reads this and links it to "Feature: Theme Toggle."
3.  **Proactive Nudge Engine:**
    *   Daily morning scan of the Graph + HubSpot + Calendar.
    *   Pushes actionable suggestions to the mobile app (e.g., "Approve drafted email to Lead X?").
4.  **Unified Inbox & Content:**
    *   Aggregates leads (HubSpot).
    *   Generates "Deep Research" content (Blogs/YouTube) with citations.

### **Technical Constraints**
*   **Frontend:** Expo SDK 54 (Text-Only, Dark Mode, Worklets for performance).
*   **Backend Router:** Netlify Functions (Webhooks/API).
*   **Agent Runner:** GitHub Actions (Deep Agents Python Script).
*   **Database:** Supabase (Postgres + Vector + Storage).
*   **AI:** Groq (Llama 3 70B).

***

## 2. System Design & Architecture

### **The "Zero-Cost Swarm" Pattern**

| Layer | Technology | Responsibility |
| :--- | :--- | :--- |
| **UI** | **Expo (React Native)** | User Interface. Subscribes to Supabase Realtime for updates. |
| **Fast Logic** | **Netlify Functions** | Receives User Commands & Webhooks. Triggers GitHub Actions. |
| **Slow Logic** | **GitHub Actions** | Runs the `deepagents` container. Executes long-running research/coding. |
| **Orchestrator** | **LangChain Deep Agents** | Handles Planning, Sub-agent delegation, and File System. |
| **Memory** | **Supabase** | **Hot Storage:** Virtual File System persistence.<br>**Cold Storage:** Graph Memory (Nodes/Edges). |

### **Data Flow: The "DevOps" Cycle**
1.  **User (Expo):** "Refactor Auth to use Supabase."
2.  **Netlify:** Triggers GitHub Action (`repository_dispatch`).
3.  **Main Agent (GitHub):** Receives task. Delegates to **DevOps Sub-Agent**.
4.  **DevOps Agent:**
    *   *Check Graph:* Reads "Coding Guidelines" node.
    *   *Plan:* Writes `refactor_plan.md` to Virtual FS.
    *   *Act:* Creates Branch -> Writes Code -> Commits -> Opens PR.
5.  **Supabase:** DevOps Agent logs "PR Created" to `tasks` table.
6.  **Expo:** Realtime update shows "PR Ready for Review."

***

## 3. Data Models (Supabase Schema)

```sql
-- 1. Shared Graph Memory (The Brain)
create table nodes (
  id uuid primary key default gen_random_uuid(),
  type text, -- 'feature', 'file', 'trend', 'metric', 'rule'
  content text,
  embedding vector(1536) -- For RAG
);

create table edges (
  source_id uuid references nodes(id),
  target_id uuid references nodes(id),
  relation text -- 'impacts', 'depends_on', 'implements', 'blocks'
);

-- 2. Virtual File System (Deep Agents Persistence)
create table agent_files (
  path text primary key,
  content text,
  last_modified timestamp default now()
);

-- 3. Task Queue (Communication with App)
create table tasks (
  id uuid primary key default gen_random_uuid(),
  status text, -- 'pending', 'processing', 'review_ready', 'done'
  input_prompt text,
  output_result text,
  agent_type text, -- 'dev', 'strategy', 'comms'
  created_at timestamp default now()
);
```

***

## 4. Code Implementation (Deep Agents)

### **A. The Swarm Configuration (`agents/swarm.py`)**
This is the Python script running inside GitHub Actions.

```python
from deepagents import create_deep_agent
from langchain_community.tools.tavily_search import TavilySearchResults
from my_tools import GithubTools, GraphMemoryTools

# 1. Define Sub-Agents
strategy_agent = {
    "name": "strategy_agent",
    "description": "Researches market trends, finance, and business logic.",
    "system_prompt": "You are the CSO. Check the 'Graph Memory' for business rules before researching. Write reports to file system.",
    "tools": [TavilySearchResults(), GraphMemoryTools.read_node]
}

devops_agent = {
    "name": "devops_agent",
    "description": "Manages code, GitHub Projects, and PRs.",
    "system_prompt": "You are the CTO. DO NOT commit to main. Always create a branch. Check 'Graph Memory' for UI constraints.",
    "tools": [
        GithubTools.create_branch, 
        GithubTools.create_pr, 
        GithubTools.write_file_to_repo,
        GraphMemoryTools.read_node
    ]
}

# 2. Middleware to persist File System to Supabase
# (Ensures 'memory' survives between GitHub Action runs)
supabase_fs_middleware = {
    "type": "filesystem",
    "config": { "backend": "supabase", "table": "agent_files" }
}

# 3. The Main Agent (CEO)
agent = create_deep_agent(
    model="groq/llama3-70b-8192",
    tools=[GraphMemoryTools.write_node], # CEO updates the Graph
    subagents=[strategy_agent, devops_agent],
    middleware=[supabase_fs_middleware],
    system_prompt="""
    You are the AutoAdmin CEO. 
    1. Plan tasks using `write_todos`.
    2. Delegate to sub-agents.
    3. Ensure all strategic decisions are logged to Graph Memory via `write_node`.
    """
)
```

### **B. The GitHub Action Runner (`.github/workflows/agent.yml`)**

```yaml
name: AutoAdmin Swarm
on:
  repository_dispatch:
    types: [start_task]
  schedule:
    - cron: "0 9 * * *" # Daily Proactive Nudge

jobs:
  run-swarm:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install deepagents supabase openai tavily-python
      
      - name: Execute Agent
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          TAVILY_API_KEY: ${{ secrets.TAVILY_API_KEY }}
          INPUT_PAYLOAD: ${{ toJson(github.event.client_payload) }}
        run: python agents/run_swarm.py
```

***

## 5. Instructions for Coding Agent (Claude/GLM)

**Copy and paste this prompt to start the build:**

> **Project:** AutoAdmin (Vertical Agentic Business OS)
> **Stack:** Expo SDK 54 (Frontend), Python `deepagents` (Backend AI), Supabase (DB).
>
> **Phase 1: The Swarm Backbone**
> 1.  Set up a Python project in `agents/`. Install `langchain-ai/deepagents`.
> 2.  Implement the `SupabaseBackend` class for `deepagents` filesystem. It must read/write to the `agent_files` SQL table.
> 3.  Implement `GraphMemoryTools` (Python) that allows agents to perform RAG on the `nodes` table using `pgvector`.
> 4.  Create `swarm.py` with the 3-agent hierarchy (CEO, Strategy, DevOps).
>
> **Phase 2: The "Pocket Architect" Tools**
> 1.  Create `GithubTools.py` using `PyGithub`.
> 2.  Implement `create_branch_and_pr(file_path, new_content, description)`.
> 3.  Ensure the DevOps agent *always* reads the `repo_map` file from the virtual filesystem before coding.
>
> **Phase 3: The Frontend (Expo)**
> 1.  Scaffold Expo with `react-compiler` enabled.
> 2.  Use `react-native-worklets-core` for any client-side sorting of the "Unified Inbox."
> 3.  Connect `useSupabaseRealtime` hook to the `tasks` table to show Agent progress.
>
> **Critical Rule:** The App never calls OpenAI directly. It POSTs a task to Netlify, which triggers the GitHub Action.

***

### Final Summary
This architecture satisfies every single one of your requirements:
*   **Vertical Partner:** Dedicated Strategy & DevOps agents.
*   **Proactive:** Morning Cron Nudges.
*   **Shared Memory:** Supabase Graph + Deep Agents File System.
*   **Deep Research:** Deep Agents "Plan & Loop" capability.
*   **Free Tier:** GitHub Actions + Groq + Supabase.

You have the map. Good luck.
