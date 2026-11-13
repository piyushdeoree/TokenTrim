## Model pricing
| Model | Base input tokens | 5m cache writes | 1h cache writes | Cache hits and refreshes | Output tokens |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Claude Sonnet 4.6 | $3 / MTok | $3.75 / MTok | $6 / MTok | $0.30 / MTok | $15 / MTok |
| Claude Haiku 5.5 (for prompts up to 100,000 tokens) | $0.10 / MTok | $0.125 / MTok | $0.20 / MTok | $0.01 / MTok | $0.50 / MTok |
| Claude Haiku 5.5 (for prompts over 100,000 tokens) | $0.50 / MTok | $0.625 / MTok | $1 / MTok | $0.05 / MTok | $2.50 / MTok |

### Batch processing
| Model | Batch input | Batch output |
| :--- | :--- | :--- |
| Claude Sonnet 4.6 | $1.50 / MTok | $7.50 / MTok |
| Claude Haiku 5.5 (for prompts up to 100,000 tokens) | $0.05 / MTok | $0.25 / MTok |
| Claude Haiku 5.5 (for prompts over 100,000 tokens) | $0.25 / MTok | $1.25 / MTok |

### Fast mode pricing
| Model | Input | Output |
| :--- | :--- | :--- |
| Claude Sonnet 4.6 | $6 USD / MTok | $30 USD / MTok |
