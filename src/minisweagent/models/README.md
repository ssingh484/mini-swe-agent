# LM interfaces

**Note: This project now uses a LiteLLM proxy instead of the LiteLLM SDK directly.**

You only need one of the model classes.

* [Default] `litellm_model.py` - Wrapper that connects to a [LiteLLM proxy](https://docs.litellm.ai/docs/proxy/quick_start)
   using OpenAI client (supports all models via proxy).
* See an overview of all models at https://mini-swe-agent.com/latest/reference/models/overview/
* See [LITELLM_PROXY_MIGRATION.md](../../LITELLM_PROXY_MIGRATION.md) for setup instructions.