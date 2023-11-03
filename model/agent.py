from datetime import datetime
import fcntl
import json
import logging
import multiprocessing
import os
from threading import Thread

from langchain.callbacks.base import BaseCallbackHandler
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
import tiktoken

from .diffbot import DiffbotClient
from .prompts import BASIC_SUMMARIZE, BIAS_REPORT, FACTUAL_CLAIMS, SLANT_DESCRIPTION


DIFFBOT_API_KEY = os.environ['DIFFBOT_API_KEY']
REQUEST_LOG_FILE = os.environ['REQUEST_LOG_FILE']

MAX_MODEL_CONTEXT = {
    'gpt-3.5-turbo': 4096,
    'text-davinci-003': 4096,
    'gpt-4': 8192,
}


class OpenAIStreamHandler(BaseCallbackHandler):
    def __init__(self, stream_queue, *args, **kwargs):
        super(OpenAIStreamHandler, self).__init__(*args, **kwargs)
        self.stream_queue = stream_queue

    def on_llm_new_token(self, token, *args, **kwargs):
        self.stream_queue.put(token)

    def on_llm_end(self, *args, **kwargs):
        self.stream_queue.put(False)


class Agent(multiprocessing.Process):
    def __init__(self, in_queue, out_queue):
        super(Agent, self).__init__()
        logging.basicConfig(filename='/var/log/build/sunlight.out', level=logging.INFO)

        self.in_queue = in_queue
        self.out_queue = out_queue

        self.fact_prompt = PromptTemplate(input_variables=['headline', 'body'], template=FACTUAL_CLAIMS)
        self.critique_prompt = PromptTemplate(input_variables=['headline', 'body'], template=BIAS_REPORT)
        self.slant_prompt = PromptTemplate(input_variables=['bias_report'], template=SLANT_DESCRIPTION)
        self.despin_prompt = PromptTemplate(input_variables=['headline', 'body', 'bias_report'], template=BASIC_SUMMARIZE)

        gpt35 = ChatOpenAI(model_name='gpt-3.5-turbo', temperature=0.0, request_timeout=300)
        davinci = ChatOpenAI(model_name='text-davinci-003', temperature=0.0, request_timeout=300)
        gpt4 = ChatOpenAI(model_name='gpt-4', temperature=0.0, request_timeout=900)

        self.stream_queue = multiprocessing.Queue()
        gpt4_stream = ChatOpenAI(
            model_name='gpt-4',
            temperature=0.0,
            streaming=True,
            callbacks=[OpenAIStreamHandler(stream_queue=self.stream_queue)],
            request_timeout=900,
        )

        self.fact_chains = {
            'gpt-3.5-turbo': LLMChain(llm=gpt35, prompt=self.fact_prompt),
            'text-davinci-003': LLMChain(llm=davinci, prompt=self.fact_prompt),
            'gpt-4': LLMChain(llm=gpt4_stream, prompt=self.fact_prompt),
        }

        self.critique_chains = {
            'gpt-3.5-turbo': LLMChain(llm=gpt35, prompt=self.critique_prompt),
            'text-davinci-003': LLMChain(llm=davinci, prompt=self.critique_prompt),
            'gpt-4': LLMChain(llm=gpt4_stream, prompt=self.critique_prompt),
        }

        self.slant_chains = {
            'gpt-3.5-turbo': LLMChain(llm=gpt35, prompt=self.slant_prompt),
            'text-davinci-003': LLMChain(llm=davinci, prompt=self.slant_prompt),
            'gpt-4': LLMChain(llm=gpt4, prompt=self.slant_prompt),
        }

        self.despin_chains = {
            'gpt-3.5-turbo': LLMChain(llm=gpt35, prompt=self.despin_prompt),
            'text-davinci-003': LLMChain(llm=davinci, prompt=self.despin_prompt),
            'gpt-4': LLMChain(llm=gpt4_stream, prompt=self.despin_prompt),
        }

        self._load_processed_jobs()

    def run(self):
        logging.basicConfig(filename='/var/log/build/sunlight.out', level=logging.INFO)
        diffbot = DiffbotClient()

        while True:
            next_job = self.in_queue.get()
            job_id = next_job['job_id']
            self.out_queue.put(('LAST_JOB_IDX', next_job['job_idx']))
            url = next_job['url']
            # XXX: Uncomment to configure model via client request
            model = 'gpt-4'  # next_job.get('model', 'gpt-3.5-turbo')
            phone_number = next_job.get('phone_number')

            logging.info(f'Processing job {job_id} for URL {url} using {model}')

            try:
                self._update_job_status(job_id, url, 'Fetching article')
                response = diffbot.request(url, DIFFBOT_API_KEY, 'article')

                if 'errorCode' in response:
                    logging.error(f'Diffbot request for {url} failed with error: {json.dumps(response)}')
                    raise Exception('REMOTE_ERROR')

                original_headline = response['objects'][0]['title']
                original_body = response['objects'][0]['text']

                self._update_job_status(job_id, url, 'Checking context length')
                trimmed_body = self._check_content_length(model, original_headline, original_body)

                result = {}

                self._update_job_status(job_id, url, 'Analyzing claims')
                Thread(
                    target=self.fact_chains[model].run,
                    kwargs={'headline': original_headline, 'body': trimmed_body},
                ).start()
                result['factual_claims'], stream_active = u'\u2022 ', True
                while stream_active:
                    next_token = self.stream_queue.get()
                    if type(next_token) is bool:
                        stream_active = next_token
                    else:
                        result['factual_claims'] += next_token
                        self._update_job_status(job_id, url, 'Analyzing claims', result=result, log_status=False)
                result['factual_claims'] = result['factual_claims'].strip()

                self._update_job_status(job_id, url, 'Critiquing bias', result=result)

                Thread(
                    target=self.critique_chains[model].run,
                    kwargs={'headline': original_headline, 'body': trimmed_body},
                ).start()

                result['bias_report'], stream_active = u'', True
                while stream_active:
                    next_token = self.stream_queue.get()
                    if type(next_token) is bool:
                        stream_active = next_token
                    else:
                        result['bias_report'] += next_token
                        self._update_job_status(job_id, url, 'Identifying slant', result=result, log_status=False)
                result['bias_report'] = result['bias_report'].strip()

                self._update_job_status(job_id, url, 'Identifying slant', result=result)
                result['original_slant'] = self.slant_chains['gpt-3.5-turbo'].run(bias_report=result['bias_report'])

                self._update_job_status(job_id, url, 'Adjusting rhetoric', result=result)
                Thread(
                    target=self.despin_chains[model].run,
                    kwargs={
                        'headline': original_headline,
                        'body': trimmed_body,
                        'bias_report': result['bias_report'],
                    },
                ).start()

                processed_output, stream_active = u'', True
                while stream_active:
                    next_token = self.stream_queue.get()
                    if type(next_token) is bool:
                        stream_active = next_token
                    else:
                        processed_output += next_token
                        article_segments = processed_output.split('###')
                        headline, body = u'', u''
                        if len(article_segments) > 0:
                            headline = article_segments[0].strip()
                        if len(article_segments) > 1:
                            body = '\n'.join(article_segments[1].split('\n')[1:]).strip()

                        ARTICLES = ['The ', ' the ', ' a ', ' an ', 'An ']
                        for word in ARTICLES:
                            headline = headline.replace(word, ' ').strip()
                        headline = headline.replace('United States', 'US')

                        result['headline'], result['body'] = headline, body
                        self._update_job_status(job_id, url, 'Adjusting rhetoric', result=result, log_status=False)

                result['cut_percent'] = int((1. - (len(body) / len(original_body))) * 100.) if original_body else 0
                result['description'] = f'Found issues to remove in {result["cut_percent"]}% of this article. Read ' \
                                        f'the full bias report for more details.'
                if phone_number:
                    result['phone_number'] = phone_number

                self._write_processed_job(job_id, url, result)
                self._update_job_status(job_id, url, 'Complete', result=result)
            except Exception as err:
                self._update_job_status(job_id, url, 'Failed', error=str(err))

    def _write_processed_job(self, job_id, url, result):
        log_msg = result | {'job_id': job_id, 'url': url, 'run_time': datetime.utcnow().isoformat()}
        with open(REQUEST_LOG_FILE, 'a') as log_file:
            fcntl.flock(log_file, fcntl.LOCK_EX)
            log_file.write(json.dumps(log_msg) + '\n')
            fcntl.flock(log_file, fcntl.LOCK_UN)

    def _load_processed_jobs(self):
        if not os.path.exists(REQUEST_LOG_FILE):
            logging.warning('Could not load processed jobs from disk; file does not exist')
            return

        with open(REQUEST_LOG_FILE, 'r') as log_file:
            fcntl.flock(log_file, fcntl.LOCK_EX)
            num_loaded = 0
            for line in log_file:
                processed_job = json.loads(line)
                self._update_job_status(
                    processed_job['job_id'],
                    processed_job['url'],
                    status='Complete',
                    result={
                        'factual_claims': processed_job['factual_claims'],
                        'bias_report': processed_job['bias_report'],
                        'original_slant': processed_job['original_slant'],
                        'headline': processed_job['headline'],
                        'body': processed_job['body'],
                        'cut_percent': processed_job['cut_percent'],
                        'description': processed_job['description'],
                    },
                )
                num_loaded += 1
            fcntl.flock(log_file, fcntl.LOCK_UN)
            logging.info(f'Loaded {num_loaded} processed jobs from disk')

    def _update_job_status(self, job_id, url, status, result=None, error=None, log_status=True):
        if log_status:
            logging.info(f'Job {job_id} now {status}')
        status_msg = {'status': status, 'url': url}
        if result:
            status_msg['result'] = result
        if error:
            status_msg['error'] = error
        self.out_queue.put((job_id, status_msg))

    def _check_content_length(self, model, headline, body):
        encoding = tiktoken.get_encoding('cl100k_base')
        max_tokens = int((MAX_MODEL_CONTEXT[model] - len(encoding.encode(BASIC_SUMMARIZE))) * 3/5)

        headline_tokens, body_tokens = encoding.encode(headline), encoding.encode(body)
        if len(headline_tokens) + len(body_tokens) < max_tokens:
            return body
        else:
            logging.warning(f'Truncating body from {len(body_tokens)} to {max_tokens - len(headline_tokens)}')
            return encoding.decode(body_tokens[:max_tokens - len(headline_tokens)]) + '... [END ARTICLE]'

    def _stream_llm_output(self, job_id, url, result, output_field, output_prefix, status, llm_chain, chain_params):
        self._update_job_status(job_id, url, status)
        Thread(target=llm_chain.run, kwargs=chain_params).start()
        result[output_field], stream_active = output_prefix, True
        while stream_active:
            next_token = self.stream_queue.get()
            if type(next_token) is bool:
                stream_active = next_token
            else:
                result[output_field] += next_token
                self._update_job_status(job_id, url, status, result=result)
        result[output_field] = result[output_field].strip()
