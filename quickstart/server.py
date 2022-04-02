import falcon
import falcon.asgi


# Because Falcon follows REST, we think in terms of resources and state
# transitions, mapping to HTTP verbs.
class ThingsResource:
    async def on_get(self, request, response):
        """Handles GET requests"""
        response.status = falcon.HTTP_200  # this is the default status
        response.content_type = falcon.MEDIA_TEXT  # default is JSON, so this is an override
        response.text = "Hello, world!"


# Instances of falcon.asgi.App are callable ASGI applications.
# In larger applications, the app will have its own file and will be created
# there.
app = falcon.asgi.App()

# Resources are represented by long-lived class instances
things = ThingsResource()

# things will handle all requests to the `/things' URL path.
app.add_route('/things', things)
