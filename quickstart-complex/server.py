import json
import logging
import uuid

import falcon
import falcon.asgi
import httpx


class StorageEngine:
    async def get_things(self, marker, limit):
        return [{'id': str(uuid.uuid4()), 'color': 'green'}]

    async def add_thing(self, thing):
        thing['id'] = str(uuid.uuid4())
        return thing


class StorageError(Exception):
    @staticmethod
    async def handle(exception, request, response, parameters):
        # TODO: log the error, clean up, etc before raising
        raise falcon.HTTPInternalServerError()


class SinkAdapter:
    engines = {
        'ddg': 'https://duckduckgo.com',
        'y': 'https://search.yahoo.com/search',
    }

    async def __call__(self, request, response, engine):
        url = self.engines[engine]
        params = {'q': request.get_param('q', True)}

        async with httpx.AsyncClient() as client:
            result = await client.get(url, params=params)

        response.status = result.status_code
        response.content_type = result.headers['content-type']
        response.text = result.text


class AuthMiddleware:
    async def process_Request(self, request, response):
        token = request.get_header('Authorization')
        account_id = request.get_header('Account-ID')

        challenges = ['Token type="Fernet"']

        if token is None:
            description = "Please provide an auth token as part of the request"
            raise falcon.HTTPUnauthorized(
                title='Auth token required',
                description=description,
                challenges=challenges,
                href='http://docs.example.com/auth'
            )

        if not self._token_is_valid(token, account_id):
            description = (
                "The provided auth token is not valid. "
                "Please request a new token and try again."
            )
            raise falcon.HTTPUnauthorized(
                title='Authentication required',
                description=description,
                challenges=challenges,
                href='http://docs.example.com/auth'
            )

    def _token_is_valid(self, token, account_id):
        return True  # But we could fill this out with a real validity check


class RequireJSON:
    async def process_request(self, request, response):
        if not request.client_accepts_json:
            raise falcon.HTTPNotAcceptable(
                description='This API only accepts JSON-encoded responses.',
                href='http://docs.examples.com/api/json'
            )

        if req.method in ('POST', 'PUT'):
            if 'application/json' not in req.content_type:
                raise falcon.HTTPUnsupportedMediaType(
                    title='This API only supports requests encoded as JSON',
                    href='http://docs.examples.com/api/json'
                )


class JSONTranslator:
    # The falcon docs say we would normally use request.get_media() and
    # response.media for this particular use case; this class only serves to
    # illustrate what's possible.

    async def process_request(self, request, response):
        # We're explicityly testing for 0, since this property could be None if
        # the Content-Length header is missing, in which case we can't know if
        # there's a request body without actually attempting to read it from
        # the request stream.
        if request.content_length == 0:
            return  # nothing to do

        body = await request.stream.read()
        if not body:
            raise falcon.HTTPBadRequest(
                title='Empty request body',
                description='A valid JSON document is required.'
            )

        try:
            request.context.doc = json.loads(body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            description = (
                'Could not decode the request body.  The JSON was '
                'incorrect or not encoded as UTF-8')
            raise falcon.HTTPBadRequest(title='Malformed JSON',
                                        description=description)

    async def process_response(self, request, response, resource,
                               request_succeeded):
        if not hasattr(response.context, 'result'):
            return
        response.text = json.dumps(response.context.result)


def max_body(limit):
    async def hook(request, response, resource, params):
        length = request.content_length
        if length is not None and length > limit:
            message = (
                "The size of the request is too large. The body must not "
                f"exceed {limit} bytes in length."
            )
            raise falcon.HTTPPayloadTooLarge(
                title='Request body is too large', description=message)


class ThingsResource:
    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger(f'thingsapp.{__name__}')

    async def on_get(self, request, response, user_id):
        marker = request.get_param('marker') or ''
        limit = request.get_param_as_int('limit') or 50

        try:
            result = await self.db.get_things(marker, limit)
        except Exception as ex:
            self.logger.error(ex)

            description = 'Aliens have attacked! Service is down.'
            raise falcon.HTTPServiceUnavailable(
                title='Service Outage', description=description,
                retry_after=30)
        # NOTE: Normally we'd use response.media for this sort of thing; this
        # example serves only to demonstrate how the context can be used to
        # pass arbitrary values between middleware component, hooks and
        # resource.
        response.context.result = result

        response.set_header('Powered-By', 'Falcon')
        response.status = falcon.HTTP_200

    @falcon.before(max_body(64 * 1024))
    async def on_post(self, request, response, user_id):
        try:
            doc = request.context.doc
        except AttributeError:
            raise falcon.HTTPBadRequest(
                title='Missing thing',
                description='A thing must be submitted in the request body.'
            )

        proper_thing = await self.db.add_thing(doc)

        response.status = falcon.HTTP_201
        response.location = f'/{user_id}/things/{proper_thing["id"]}'


# The app instance is an ASGI callable
app = falcon.asgi.App(
    middleware=[
        # AuthMiddleware(),
        RequireJSON(),
        JSONTranslator(),
    ]
)

db = StorageEngine()
things = ThingsResource(db)
app.add_route('/{user_id}/things', things)

# If a responder ever raises an instance of StorageError, pass control to this
# handler.
app.add_error_handler(StorageError, StorageError.handle)

# Proxy some things to another service.
# This example shows how we might send parts of an API off to a legacy system
# that hasn't been upgraded yet or perhaps is a single, shared cluster across
# multiple groups or data centers.
sink = SinkAdapter()
app.add_sink(sink, r'/search/(?P<engine>ddg|y)\Z')
