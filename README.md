# ☀️ Sunlight

## Introduction

Welcome to **Sunlight**, an open-source tool designed to illuminate your writing with the power of Large Language Models (LLMs). Sunlight analyzes and critiques writing for biases, providing suggestions for clarity and objectivity. Whether you're composing an article, drafting a report, or crafting a narrative, look to Sunlight for a second opinion to ensure fairness and a balanced perspective.

## [Live Demo](https://sunlight.a16z.ai)


## Local Installation

Getting started with Sunlight is very easy, thanks to containerization. Follow these simple steps to install and run Sunlight on your system:

### Prerequisites

Before proceeding, ensure you have a recent version of Docker installed. If you need to install Docker, please follow the instructions on the [Docker installation page](https://docs.docker.com/get-docker/).

### Setup Instructions

1. Clone this repository and navigate to the resulting directory.
2. Edit the `service.cfg` file with your API credentials for Diffbot and OpenAI. Include Telnyx credentials if you wish to enable the SMS integration.
3. Execute `run.sh`. This will:

   - Load the environment variables from `service.cfg`.
   - Build a Docker image with all necessary dependencies.
   - Run the Docker image, which includes the backend API server along with a demo web UI.

```
git clone https://github.com/a16z-infra/sunlight
vi service.cfg
. run.sh
```

### Using Sunlight

After executing `run.sh`, Sunlight will be operational. Access the demo web UI by visiting:

http://localhost:8888/static/index.html

Follow the on-page instructions to configure the target document and model version.

## How does this work?

Sunlight runs a simple backend service that interfaces with LLMs for the interesting semantic analysis. You can check this repository for implementation details, but here's a basic overview of what happens under the hood:

- **Input**: Users submit a link to their writing via SMS or the web UI.
- **Pre-processing**: The API server fetches page tags and then calls out to [Diffbot](https://diffbot.com) for structured metadata, including the title and body text, upon job submission.
- **Processing**: Text is passed through a short cascade of parameterized prompts for semantic analysis.
- **Evaluation**: Suggestions for improvement are passed back to the user.

## What are the prompts?

Sunlight uses a series of carefully crafted prompts to guide the LLMs in assessing your writing. You can find the current versions [here](https://github.com/a16z-infra/sunlight/blob/main/model/prompts.py). Here’s how it works:

1. **Fact extraction**: identify, condense, and reorder claims made in your writing
2. **Bias analysis**: assess your piece's underlying perspective in a brief report
3. **Slant tagging**: using the bias report, assign a short label for categorization
4. **Copy editing**: combining the above elements, rework the piece for objectivity while retaining the same factual skeleton

## Disclaimer

Please read our [Terms of Service](https://sunlight.a16z.ai/static/terms_of_service.txt) and [Privacy Policy](https://sunlight.a16z.ai/static/privacy_policy.txt) before using Sunlight.

Sunlight may produce inaccurate information. This demo utilizes experimental large language model technology to generate its outputs, and we make no guarantees or promises regarding the accuracy or suitability of its analysis. This demo makes no claim to correct factual errors in the underlying source content.

It is incapable of providing investment advice, legal advice or marketing financial advisory advice, or soliciting investors or clients (and it is not intended to be utilized by investors); therefore its output should not be used as such.

---

Thanks for checking out our tool and reading this far. We hope Sunlight is useful to you  Community contributions, feedback, and insights are what make open-source projects successful; please reach out with any comments or suggestions.

