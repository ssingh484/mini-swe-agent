# LiteLLM Proxy Migration Guide

This project has been updated to use a LiteLLM proxy instead of the LiteLLM SDK directly. This change provides better flexibility for deployment and model management.

## What Changed

### Architecture
- **Before**: Direct LiteLLM SDK calls (`litellm.completion()`)
- **After**: OpenAI client pointing to LiteLLM proxy endpoint

### Key Changes
1. **Core models** now use OpenAI client with configurable proxy URL
2. **LiteLLM dependency** is now optional (only needed for cost tracking)
3. **New configuration options** for proxy URL and API key

## Configuration

### Environment Variables

Set these environment variables to configure the proxy:

```bash
# LiteLLM Proxy URL (default: http://localhost:4000)
export LITELLM_PROXY_BASE_URL=http://localhost:4000

# API Key for the proxy (default: sk-1234)
export LITELLM_PROXY_API_KEY=your-api-key

# Optional: Enable cost tracking (requires litellm package)
pip install litellm
```

### Python Configuration

```python
from minisweagent.models.litellm_model import LitellmModel

# Using environment variables (recommended)
model = LitellmModel(model_name="gpt-4")

# Or configure explicitly
model = LitellmModel(
    model_name="gpt-4",
    proxy_base_url="http://localhost:4000",
    api_key="your-api-key",
)
```

## Setting Up LiteLLM Proxy

### Basic Setup

1. **Install LiteLLM**:
```bash
pip install litellm[proxy]
```

2. **Create config.yaml**:
```yaml
model_list:
  - model_name: gpt-4
    litellm_params:
      model: gpt-4
      api_key: os.environ/OPENAI_API_KEY
  - model_name: claude-3-opus
    litellm_params:
      model: anthropic/claude-3-opus-20240229
      api_key: os.environ/ANTHROPIC_API_KEY
```

3. **Start the proxy**:
```bash
litellm --config config.yaml --port 4000
```

### Docker Setup

```dockerfile
FROM ghcr.io/berriai/litellm:latest

COPY config.yaml /app/config.yaml

CMD ["--config", "/app/config.yaml", "--port", "4000"]
```

```bash
docker run -p 4000:4000 -v $(pwd)/config.yaml:/app/config.yaml litellm
```

## Cost Tracking

Cost tracking is optional and requires the `litellm` package:

```bash
# Install litellm for cost tracking
pip install litellm

# Or install with mini-swe-agent
pip install mini-swe-agent[cost-tracking]
```

If you don't need cost tracking, you can disable it:

```python
model = LitellmModel(
    model_name="gpt-4",
    cost_tracking="ignore_errors",
)
```

Or globally:
```bash
export MSWEA_COST_TRACKING=ignore_errors
```

## Response API Support

The `LitellmResponseModel` uses the LiteLLM Response API format. Ensure your proxy has the `/v1/responses` endpoint enabled. This is a custom LiteLLM feature that may not be supported by all proxy deployments.

If you encounter issues:
1. Check your LiteLLM proxy version
2. Verify the endpoint is enabled in your proxy configuration
3. Consider using the standard `LitellmModel` class instead

## Troubleshooting

### Connection Refused
- Ensure the proxy is running: `curl http://localhost:4000/health`
- Check the proxy URL configuration

### Authentication Errors
- Verify your API key is correct
- Check that the proxy has the correct upstream API keys configured

### Cost Tracking Errors
- Install litellm: `pip install litellm`
- Or disable cost tracking: `cost_tracking="ignore_errors"`

### Model Not Found
- Verify the model is configured in your proxy's config.yaml
- Check the proxy logs for model loading errors

## Migration Checklist

- [ ] Deploy LiteLLM proxy
- [ ] Update environment variables (`LITELLM_PROXY_BASE_URL`, `LITELLM_PROXY_API_KEY`)
- [ ] Test basic model calls
- [ ] Verify cost tracking works (if needed)
- [ ] Update any custom model configurations
- [ ] Test Response API models (if used)

## Benefits of Proxy Approach

1. **Centralized Configuration**: Manage all model configurations in one place
2. **Better Monitoring**: Proxy provides unified logging and metrics
3. **Cost Control**: Implement rate limiting and budget controls at proxy level
4. **Flexibility**: Easily switch between providers without code changes
5. **Caching**: Proxy can implement response caching
6. **Load Balancing**: Distribute requests across multiple API keys

## Rollback

If you need to rollback to the direct SDK approach, you can:
1. Reinstall an older version: `pip install mini-swe-agent==<old_version>`
2. Or modify the code to use `litellm.completion()` directly

Note: We recommend using the proxy approach going forward for better scalability and management.
