FACTUAL_CLAIMS = u'''Summarize the factual claims made in this article in a bullet-point list.
Instructions:
1. Order the facts by decreasing importance
2. Use extremely concise, simple language

### Headline:
{headline}

### Body:
{body}:

### Factual Claims:
\u2022 '''

BIAS_REPORT = '''Critique the following possibly-biased article.
Instructions:
1. Identify any bias -- especially political bias.
2. If the article is fair, be fair in your critique. If it is biased, be harsh and critical about the issues.
3. Use specific examples and quote directly where possible.
4. Call out any opinion, hyperbole, and speculation.
5. Assess where this article lies on the political spectrum.
6. Write the critique as 3-5 paragraphs separated by two (2) newline characters.

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

BASIC_SUMMARIZE = '''Rewrite the following article according to the instructions.
Instructions:
1. Remove all bias, opinion, hyperbole, speculation, and forward-looking statements -- especially any described in the Bias Report.
2. Rewrite into an objective, professional tone using entirely new language; eliminate flourishes and creative style.
3. Use erudite, pithy language in novel expressions.
4. Reorder information in the inverted pyramid style: most important to least.
5. Do not misreport facts from the original article; include important factual details.
6. Attribute all direct quotes using quotation marks.
7. Split into multiple paragraphs separated by two (2) newline characters.
8. Use markdown h3 elements ### to distinguish the Edited Headline and Edited Body.

### Headline:
{headline}

### Body:
{body}

### Bias Report:
{bias_report}

### Edited Headline:
'''
