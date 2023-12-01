FACTUAL_CLAIMS = u'''Summarize the factual claims made in this article in a bulleted list separated by \u2022 unless it is too short.
Instructions:
1. Order the facts by decreasing importance
2. Use extremely concise, simple language
3. If the article is very short or truncated, request that user elaborate or re-host.

### Headline:
{headline}

### Body:
{body}:

### Factual Claims:
'''

BIAS_REPORT = '''Critique the following possibly-biased article unless it is too short.
Instructions:
1. Identify any bias -- especially political bias.
2. If the article is fair, be fair in your critique. If it is biased, be harsh and critical about the issues.
3. Use specific examples and quote directly where possible.
4. Call out any opinion, hyperbole, and speculation.
5. Assess where this article lies on the political spectrum.
6. Write the critique as 3-5 paragraphs separated by two (2) newline characters.
7. If the article is very short or truncated, explain the problem in one paragraph and do not critique it.

### Headline:
{headline}

### Body:
{body}

### Critical Review:
'''

SLANT_DESCRIPTION = '''Describe the slant critiqued in the following Bias Report in 1-2 words. Be creative, pithy, and accurate.
Example slants: Fair, Left-leaning, Extreme Right, Environmentalist, Bitcoin Maximalist, Conservative, Conspiracist, Impartial

### Bias Report:
{bias_report}

### Slant:
'''
