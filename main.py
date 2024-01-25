from werkzeug.middleware.proxy_fix import ProxyFix
from flask_limiter.util import get_remote_address
from flask_limiter import Limiter
import flask
import json
import time

from utils import ScrapeData, ParseProfile, ScrapeThree, CacheHandler

scraper = ScrapeData()
three = ScrapeThree()
cache = CacheHandler()

app = flask.Flask(__name__, static_folder = 'static')
app.wsgi_app = ProxyFix(app.wsgi_app, x_for = 1)
limiter = Limiter(app,
    key_func = get_remote_address,
    default_limits = ["5 per minute"]
)

@app.errorhandler(429)
@limiter.exempt
def status_page_429(error):
    return flask.render_template('429.html'), 429

@app.errorhandler(404)
@limiter.exempt
def status_page_404(error):
    return flask.render_template('404.html'), 404

@app.errorhandler(500)
@limiter.exempt
def status_page_500(error):
    return flask.render_template('500.html'), 500


@app.route('/http/404')
@limiter.exempt
def http404():
    return flask.render_template('404.html'), 200

@app.route('/http/429')
@limiter.exempt
def http429():
    return flask.render_template('429.html'), 200

@app.route('/http/500')
@limiter.exempt
def http500():
    return flask.render_template('500.html'), 200


@app.route('/robots.txt')
@limiter.exempt
def robots():
    return flask.send_from_directory(app.static_folder, 'robots.txt'), 200

@app.route('/')
@limiter.limit("5 per second")
def index():
    return flask.render_template('index.html'), 200

@app.route('/lookup/<name>', methods = ['GET'])
def lookup(name):
    name = name.lower()

    parser = ParseProfile()
    data, status_code = cache.find(name, scraper, parser)
    
    return app.response_class(response = json.dumps(data, indent = 2), status = status_code, mimetype = 'application/json')

@app.route('/three', methods = ['GET'])
def _three():
    names = three.get_names()
    return app.response_class(response = json.dumps(names, indent = 2), status = 200, mimetype = 'application/json')


three.setup(scraper)
app.run(host = '0.0.0.0', port = 80)
