# CMPE 258 Auto-Bug-Squashing Agent (Gemma 4 Edition)
## An Autonomous AI Safety Net for the Future of Education

### Track
Special Technology Track: **Ollama**  
Impact Track: **Future of Education**

---

### Introduction: The Solitude of the Junior Developer
Every new programmer encounters a moment of deep frustration: a massive traceback that halts their progress. While experienced developers have built an intuition for interpreting raw stack traces, learners often resort to endless copy-pasting into stack overflow or chat interfaces, resulting in disjointed context and "hallucinated" un-runnable code.

Our objective was to build a system that acts as a localized **AI Coding Tutor** built specifically on the **Gemma 4** open-weights model using **Ollama**.

### System Architecture
The CMPE 258 Bug Squashing Agent departs from typical deterministic loops or linear scripts. Instead, it features an autonomous multi-turn Swarm Coordinator built entirely from scratch in Python.

1. **Gemma 4 as the Core Logic Engine**
   We implemented a standalone `Gemma4Model` integration that runs securely and locally via `http://localhost:11434/api/chat`. By routing context locally, students can securely analyze homework assignments or proprietary logic without transmitting logic across the internet.

2. **Native Tool Calling**
   Gemma 4 is presented with Python function tools (`read_file`, `edit_file`, and `run_bash` for running pytest traces). It autonomously navigates the project structure, analyzes errors, and tests hypothesis just like a human engineer would.

3. **The "Dream" Consolidation System**
   Drawing inspiration from advanced orchestration patterns, our `Memory` module features a `consolidate_dream()` mechanism. Following a successful debug loop, Gemma 4 is used to extract a "durable learning" — identifying the actual syntactic misunderstanding (e.g. incorrect variable scoping) rather than just leaving the user with patched code.

### Why Gemma 4 and Ollama?
For an educational tool that requires strict data privacy, local latency, and the robust reasoning needed for software bug squashing, running **Gemma 4 local-first via Ollama** was the clear path forward. It proved immensely capable at maintaining context across deep tracebacks and reliably generating and sending strict schemas to our simulated tool endpoints.

### Future Impacts
By open-sourcing this tool, we empower students to learn debugging. Instead of a standard chatbot interface, they can watch Gemma 4 explore files via the interactive CLI (powered by `rich`), providing a transparent view into how professional debugging is structured.

### Required Media Attachments
*(Please link your YouTube video Demo here)*
*(Please link your Code Repository here)*
