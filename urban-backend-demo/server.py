"""
One endpoint with immediate response
One endpoint with job submission
Database: track job IDs, user session/token, job completion status
The function that executes the submitted job should produce a file that should be served in the public results store once the job completes.
One endpoint to check the status of a job
Have a script demonstrating the API calls
"""
import logging
import queue
import sqlite3
import threading
import time
import uuid

import falcon
import falcon.asgi

logging.basicConfig(level=logging.ERROR)
LOGGER = logging.getLogger('demo')
SENTINEL = 'stop'


class Echo:
    async def on_get(self, request, response):
        """Handle get request."""
        response.status = falcon.HTTP_200
        response_media = {}
        for key, value in request.params.items():
            response_media[key] = value

        response.media = response_media


class JobsManager:
    def __init__(self):
        connection = sqlite3.connect('database.sqlite')
        with connection:
            connection.execute(
                'CREATE TABLE IF NOT EXISTS jobs (id text, status text)')
        connection.close()
        self.queue = queue.Queue()
        self.worker = threading.Thread(target=self._job_worker,
                                       args=[self.queue])
        self.worker.start()

    def _job_worker(self, queue):
        while True:
            time.sleep(3)  # sleep in order to demonstrate pending status

            job_id = queue.get()
            if job_id == SENTINEL:
                break

            connection = sqlite3.connect('database.sqlite')
            with connection:
                connection.execute(
                    'UPDATE jobs SET status = "started" '
                    f'WHERE id = "{job_id}"')
            connection.close()

            time.sleep(3)

            connection = sqlite3.connect('database.sqlite')
            with connection:
                connection.execute(
                    'UPDATE jobs SET status = "complete" '
                    f'WHERE id = "{job_id}"')
            connection.close()

    # GET retrieves status
    async def on_get(self, request, response):
        connection = sqlite3.connect('database.sqlite')
        with connection:
            result = connection.execute(
                f'SELECT status FROM jobs WHERE id = '
                f'"{request.params["id"]}"').fetchone()
        connection.close()

        if result is None:
            raise falcon.HTTPBadRequest(
                title='Job ID not found',
                description='Job ID is not valid.'
            )

        response.media = {'status': result[0]}

    # POST submits a job, returns job ID
    async def on_post(self, request, response):
        new_id = str(uuid.uuid4())
        connection = sqlite3.connect('database.sqlite')
        with connection:
            connection.execute(
                f'INSERT INTO jobs (id, status) VALUES ("{new_id}", "pending")')
        connection.close()

        self.queue.put(new_id)
        response.media = {'job_id': new_id}

# use sqlalchemy instead of sqlite

app = falcon.asgi.App()
echo = Echo()
jobs = JobsManager()

app.add_route('/echo', echo)
app.add_route('/jobs', jobs)
