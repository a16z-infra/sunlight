from concurrent.futures import ThreadPoolExecutor
import copy
import json
import logging
import multiprocessing
import os
import random
import string
from urllib.parse import urlparse

from lxml import etree
import telnyx
import tornado.gen
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
import tornado.ioloop
import tornado.web
from tornado.web import StaticFileHandler

from model.agent import Agent


HOST_DOMAIN = os.environ['HOST_DOMAIN']
APP_URL_PATH = os.environ['APP_URL_PATH']
STATIC_FILE_DIR = os.environ['STATIC_FILE_DIR']
TORNADO_SERVER_PORT = int(os.environ['TORNADO_SERVER_PORT'])
NUM_AGENTS = 6

JOB_ID_CHARS = string.ascii_lowercase + string.ascii_uppercase + string.digits
JOB_STATUS_CHECK_INTERVAL_MS = 1000

telnyx.api_key = os.environ['TELNYX_API_KEY']
TELNYX_PROFILE_ID = os.environ['TELNYX_PROFILE_ID'].encode()
TELNYX_PHONE_NUMBER = os.environ['TELNYX_PHONE_NUMBER']

UNSUPPORTED_TLDS = [
    'seekingalpha.com',
    'zacks.com',
    'tipranks.com',
    'marketbeat.com',
    'wallstreetzen.com',
    'benzinga.com',
    'indmoney.com',
    'marketwatch.com',
    'marketscreener.com',
    'stockrover.com',
    'fool.com',
    'trade-ideas.com',
    'invest.aaii.com',
    'yieldstreet.com',
    'mindfultrader.com',
    'tradingview.com',
    'alpharesearch.io',
    'morningstar.com',
    'investech.com',
    'kiplinger.com',
    'stockunlock.com',
    'barrons.com',
    'moneyweek.com',
    'investors.com',
    'readthejoe.com',
    'finance.yahoo.com',
    'google.com/finance',
]


def get_job_id():
    return ''.join(random.choices(JOB_ID_CHARS, k=8))


class FetchOpenGraphTags(tornado.web.RequestHandler):
    MAX_REQUEST_LEN = 512
    EXECUTOR = ThreadPoolExecutor(max_workers=32)

    def initialize(self, cache):
        self.cache = cache

    @tornado.gen.coroutine
    def post(self):
        if len(self.request.body) > self.MAX_REQUEST_LEN or 'url' not in self.request.body.decode('utf-8'):
            self.set_status(400)
            return

        url = json.loads(self.request.body)['url']

        if url in self.cache:
            open_graph_tags = self.cache[url]
        else:
            open_graph_tags = yield self.fetch_url_meta_tags(url)
            if type(open_graph_tags) is dict:
                open_graph_tags['tld'] = urlparse(url).netloc
            self.cache[url] = open_graph_tags

        if open_graph_tags is not None:
            self.set_status(200)
            self.write(json.dumps(open_graph_tags))
        else:
            self.set_status(400)

    @tornado.gen.coroutine
    def fetch_url_meta_tags(self, url):
        http_client = AsyncHTTPClient()
        request = HTTPRequest(url, method='GET', streaming_callback=self.handle_streaming_response)
        try:
            _ = yield http_client.fetch(request)
        except:  # NB: Cleanest way to cancel a streaming request, unfortunately
            pass

        if hasattr(self, 'html_fragment') and type(self.html_fragment) is str:
            return self.find_meta_tags(self.html_fragment)
        else:
            return None

    def handle_streaming_response(self, chunk):
        if hasattr(self, 'html_fragment'):
            self.html_fragment += chunk.decode('utf-8')
            if '</head>' in self.html_fragment or '<body>' in self.html_fragment:
                raise Exception('Cancel request')  # NB: Cleanest way to cancel a streaming request, unfortunately
        else:
            self.html_fragment = chunk.decode('utf-8')

    @staticmethod
    def find_meta_tags(html_fragment):
        parser = etree.HTMLParser()
        tree = etree.fromstring(html_fragment, parser)

        metadata = {}

        # Check for Open Graph meta tags
        og_title = tree.xpath('//meta[@property="og:title"]/@content')
        if og_title:
            metadata['title'] = og_title[0]

        og_description = tree.xpath('//meta[@property="og:description"]/@content')
        if og_description:
            metadata['description'] = og_description[0]

        og_image = tree.xpath('//meta[@property="og:image"]/@content')
        if og_image:
            metadata['image'] = og_image[0]

        # Check for Dublin Core meta tags as fallback
        if 'title' not in metadata:
            dc_title = tree.xpath('//meta[@name="DC.Title"]/@content')
            if dc_title:
                metadata['title'] = dc_title[0]

        if 'description' not in metadata:
            dc_description = tree.xpath('//meta[@name="DC.Description"]/@content')
            if dc_description:
                metadata['description'] = dc_description[0]

        # Check for Twitter card meta tags as final fallback
        if 'title' not in metadata:
            twitter_title = tree.xpath('//meta[@name="twitter:title"]/@content')
            if twitter_title:
                metadata['title'] = twitter_title[0]

        if 'description' not in metadata:
            twitter_description = tree.xpath('//meta[@name="twitter:description"]/@content')
            if twitter_description:
                metadata['description'] = twitter_description[0]

        if 'image' not in metadata:
            twitter_image = tree.xpath('//meta[@name="twitter:image"]/@content')
            if twitter_image:
                metadata['image'] = twitter_image[0]

        return metadata if len(metadata) > 0 else None


class SubmitUrlHandler(tornado.web.RequestHandler):
    def initialize(self, in_queue, job_statuses, job_ids_by_url):
        self.in_queue = in_queue
        self.job_statuses = job_statuses
        self.job_ids_by_url = job_ids_by_url

    def post(self):
        logging.info(f'Received {self.request.body}')
        request = json.loads(self.request.body)
        url, model = request['url'], request['model']

        self.set_status(200)
        if not url.startswith('http://') and not url.startswith('https://'):
            self.write({'error': 'INVALID_URL'})
        elif any(tld in url for tld in UNSUPPORTED_TLDS):
            self.write({'error': 'UNSUPPORTED_URL'})
        elif url in self.job_ids_by_url:
            self.write({'job_id': self.job_ids_by_url[url]})
        else:
            job_id = get_job_id()
            self.in_queue.put({'job_id': job_id, 'job_idx': self.job_statuses['JOB_IDX'], 'url': url, 'model': model})
            self.job_statuses[job_id] = {'status': 'Queued', 'job_idx': self.job_statuses['JOB_IDX'], 'url': url}
            self.job_ids_by_url[url] = job_id
            self.job_statuses['JOB_IDX'] += 1
            self.write({'job_id': job_id})


class FetchJobStatusHandler(tornado.web.RequestHandler):
    def initialize(self, out_queue, job_statuses):
        self.out_queue = out_queue
        self.job_statuses = job_statuses

    def get(self):
        while not self.out_queue.empty():
            job_id, status_msg = self.out_queue.get()
            self.job_statuses[job_id] = status_msg

        job_id = self.get_argument('job_id')
        status_dict = self.job_statuses.get(job_id, {'status': 'Job unknown'})
        if 'job_idx' in status_dict:
            status_dict = copy.copy(status_dict)
            status_dict['queue_position'] = status_dict['job_idx'] - self.job_statuses['LAST_JOB_IDX']
            del status_dict['job_idx']
        self.set_status(200)
        self.write(json.dumps(status_dict))


class TelnyxSMSHandler(tornado.web.RequestHandler):
    def initialize(self, in_queue, job_statuses):
        self.in_queue = in_queue
        self.job_statuses = job_statuses

    def post(self):
        if TELNYX_PROFILE_ID not in self.request.body:
            raise tornado.web.HTTPError(403)

        try:
            message = json.loads(self.request.body)
        except:
            raise tornado.web.HTTPError(400)

        if 'data' not in message or 'event_type' not in message['data']:
            raise tornado.web.HTTPError(400)

        if message['data']['event_type'] != 'message.received':
            self.set_status(200)
            return

        if 'payload' not in message['data'] or \
                'text' not in message['data']['payload'] or \
                'from' not in message['data']['payload'] or \
                'phone_number' not in message['data']['payload']['from']:
            raise tornado.web.HTTPError(400)

        text, phone_number = message['data']['payload']['text'], message['data']['payload']['from']['phone_number']

        job_id = get_job_id()
        self.in_queue.put({'job_id': job_id, 'url': text, 'phone_number': phone_number})
        self.job_statuses[job_id] = {'status': 'Queued', 'url': text}

        self.set_status(200)
        self.finish()


class StaticFileHandlerWithDefaultContentType(StaticFileHandler):
    def set_extra_headers(self, path):
        self.set_header('Content-Type', 'text/html')


@tornado.gen.coroutine
def dequeue_job_statuses(out_queue, job_statuses):
    while not out_queue.empty():
        job_id, status_msg = out_queue.get()

        if type(status_msg) is dict and status_msg['status'] == 'Complete' and 'phone_number' in status_msg['result']:
            phone_number = status_msg['result']['phone_number']
            reply_msg = f'Analyzed {status_msg["result"]["headline"]}; read at {HOST_DOMAIN}?job_id={job_id}'
            yield send_sms(phone_number, reply_msg)

        job_statuses[job_id] = status_msg


@tornado.gen.coroutine
def send_sms(reply_number, reply_msg):
    try:
        message = telnyx.Message.create(from_=TELNYX_PHONE_NUMBER, to=reply_number, text=reply_msg)

        if message['errors']:
            logging.error(f'SMS reply to {reply_number} contained errors, status: {message["errors"]}')
    except:
        logging.error(f'Failed to send SMS reply to {reply_number}', exc_info=True)


if __name__ == '__main__':
    logging.basicConfig(filename='/var/log/build/sunlight.out', level=logging.INFO)
    logging.getLogger('tornado.application').setLevel(logging.WARNING)

    with multiprocessing.Manager() as manager:
        in_queue, out_queue = multiprocessing.Queue(), multiprocessing.Queue()

        job_statuses = manager.dict()
        job_statuses['JOB_IDX'], job_statuses['LAST_JOB_IDX'] = 1, 0
        job_ids_by_url = manager.dict()

        [Agent(in_queue, out_queue).start() for _ in range(NUM_AGENTS)]

        tornado.ioloop.PeriodicCallback(
            lambda: dequeue_job_statuses(out_queue, job_statuses),
            JOB_STATUS_CHECK_INTERVAL_MS,
        ).start()

        app = tornado.web.Application([
            (r'/fetch_open_graph_tags', FetchOpenGraphTags, {'cache': {}}),
            (r'/submit_url', SubmitUrlHandler, {'in_queue': in_queue, 'job_statuses': job_statuses, 'job_ids_by_url': job_ids_by_url}),
            (r'/submit_sms', TelnyxSMSHandler, {'in_queue': in_queue, 'job_statuses': job_statuses}),
            (r'/fetch_job_status', FetchJobStatusHandler, {'out_queue': out_queue, 'job_statuses': job_statuses}),
            (r'/(.*)', StaticFileHandlerWithDefaultContentType, {'path': '/app/'}),
        ], static_path=STATIC_FILE_DIR)

        app.listen(TORNADO_SERVER_PORT)
        tornado.ioloop.IOLoop.current().start()
