### Flagship Models (Complex Reasoning & Agents)

* **Gemini 3.1 Pro**
    * **API String:** `gemini-3.1-pro`
    * **Context Window:** 2M tokens.
    * **Capabilities & Power:** The premium flagship model. Excels at multi-step reasoning, complex agentic workflows, and "vibe coding" (autonomous, high-level code architecture and generation).
    * **When/Where to Use:** Core logic engines for autonomous AI agents, complex Retrieval-Augmented Generation (RAG) over massive datasets (e.g., processing dozens of 1000-page PDFs or hours of video simultaneously), and applications where reasoning accuracy overrides latency and cost concerns.

### High-Volume & Low-Latency Models (Scale & Speed)

* **Gemini 3 Flash**
    * **API String:** `gemini-3-flash`
    * **Context Window:** 2M tokens.
    * **Capabilities & Power:** The frontier-class workhorse. Rivals the reasoning performance of legacy "Pro" models but operates at a fraction of the cost with significantly lower latency.
    * **When/Where to Use:** General-purpose AI features, standard RAG applications, real-time customer support chatbots, and high-volume multimodal processing (e.g., analyzing user-uploaded images/documents on the fly).

* **Gemini 3.1 Flash-Lite**
    * **API String:** `gemini-3.1-flash-lite`
    * **Context Window:** 1M tokens.
    * **Capabilities & Power:** The fastest and most budget-friendly multimodal model in the current lineup. Drops heavy reasoning capabilities in favor of raw throughput.
    * **When/Where to Use:** Massive-scale text classification, basic prompt routing, log parsing, and simple data extraction where cost and speed are the primary metrics.

### Specialized Native Media & Real-Time Models

* **Gemini Live API (3.1 Flash Live)**
    * **API String:** `gemini-3.1-flash-live`
    * **Capabilities:** Real-time, low-latency audio-to-audio (A2A) streaming. Bidirectional dialogue that can be interrupted naturally. Supports camera and screen-sharing inputs for contextual awareness.
    * **When/Where to Use:** Voice-first AI assistants, language tutoring apps, real-time translation tools, or accessibility overlays that "see" and discuss the user's screen or camera feed in real-time.

* **Nano Banana 2 (Gemini 3 Flash Image)**
    * **API String:** `gemini-3-flash-image`
    * **Capabilities:** State-of-the-art native image model capable of text-to-image, image+text-to-image (editing), and multi-image-to-image composition (fusion and style transfer). Replaces the older Nano Banana and Nano Banana Pro models.
    * **When/Where to Use:** In-app visual content creation, dynamic asset generation for marketing pipelines, or user-facing photo editing tools.

* **Veo 3.1**
    * **API String:** `veo-3.1`
    * **Capabilities:** High-fidelity cinematic video generation with natively synchronized audio. Executes text-to-video with audio cues, extends existing videos, or uses reference images to guide content.
    * **When/Where to Use:** Automated video ad generation, storyboarding tools, or rich-media content pipelines.

* **Lyria 3**
    * **API String:** `lyria-3`
    * **Capabilities:** Multimodal music generation (text, image, or video to music). Produces professional-grade 30-second tracks with granular control over tempo, genre, mood, and automated vocals in multiple languages.
    * **When/Where to Use:** Dynamic background music for user-generated content, royalty-free asset generation for games, or creative audio tools.

---

### Cost & API Overview (per 1 Million Tokens)

Costs are tiered for Pro models based on whether the prompt stays under or exceeds 200K tokens. Context caching allows for the storage of large, frequently used prompts (like massive system instructions or full codebase structures) at a fraction of the standard input cost.

| Model | API String | Input Cost (Standard) | Output Cost (Standard) | Cached Input Cost |
| :--- | :--- | :--- | :--- | :--- |
| **Gemini 3.1 Pro** | `gemini-3.1-pro` | $2.00 (≤200K) / $4.00 (>200K) | $12.00 (≤200K) / $18.00 (>200K) | $0.20 (≤200K) / $0.40 (>200K) |
| **Gemini 3 Flash** | `gemini-3-flash` | $0.50 | $3.00 | $0.05 |
| **Gemini 3.1 Flash-Lite** | `gemini-3.1-flash-lite` | $0.25 | $1.50 | $0.025 |

*Media Generation Costs:* Image models (`gemini-3-flash-image`) are generally priced between $0.03 to $0.06 per generated image depending on resolution (or roughly $60 to $120 per 1M output tokens). Audio (`lyria-3`) and Video (`veo-3.1`) models bill per minute or second of generated media.

---

### ⚠️ Note:
* **Caching Storage Costs:** Context caching drops per-query input costs drastically, but requires an hourly storage rate (typically $4.50/1M tokens/hour for Pro models and $1.00/1M tokens/hour for Flash models). Only cache data you will query frequently within short timeframes.
* **Media Constraints:** All music generated via Lyria 3 includes forced SynthID watermarking for AI identification. Veo models strictly enforce safety constraints and will instantly block generation of unsafe or policy-violating video content.