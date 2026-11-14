"""AWS Lambda entry point (container image): handler = stylometry.server.lambda_handler.handler"""
from mangum import Mangum

from stylometry.language import LANGUAGES
from stylometry.preprocess import get_nlp
from stylometry.server.app import app

for _lang in LANGUAGES:  # load the spaCy models once per cold start, not on the first request
    get_nlp(_lang)

handler = Mangum(app, lifespan="auto")  # starts the MCP session manager
