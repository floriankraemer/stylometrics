"""AWS Lambda entry point (container image): handler = stylometry.server.lambda_handler.handler"""
from mangum import Mangum

from stylometry.preprocess import get_nlp
from stylometry.server.app import app

get_nlp()  # load the spaCy model once per cold start, not on the first request

handler = Mangum(app, lifespan="auto")  # starts the MCP session manager
