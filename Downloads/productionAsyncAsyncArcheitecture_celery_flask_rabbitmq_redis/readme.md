# AsyncArcheitecture Services
Asynchronous architecture is a design paradigm that enables systems to handle tasks concurrently, without waiting for each task to complete before starting the next. This approach improves efficiency and responsiveness by decoupling request processing from response handling. In an asynchronous system, components communicate through non-blocking calls, allowing them to perform other operations while waiting for tasks to finish. This is particularly useful in scenarios with high latency or where tasks are I/O-bound. By leveraging event-driven programming and message queues, asynchronous architecture enhances scalability and performance, making it well-suited for modern, distributed applications.

The code is structured as a dockerized application using Flask, Celery and RabbitMQ.<br>
The architecture of the solution and the structure of the project are explained below.

## Solution architecture

![alt text](images/image7.png)

<ul>
    <li><b>Flask</b>: framework that serves the main application that exposes a minimal interface and the actual API endpoints. Chosen for fast and easy API development. Valid alternatives could be: Django, FastAPI.</li>
    <li><b>Celery</b>: workers that actually handle the elaboration while the main Flask application returns immediately an "ok" message to the client.</li>
    <li><b>RabbitMQ</b> (Redis in the picture): message broker that collects the task coming from the main application with each API call and proceeds to distribute them to one of the workers, storing the task status (PENDING, SUCCESS, FAILED) and collecting the results once the workers finish their tasks. (*)In this case (both in the picture and in our solution) we are using the same technology to collect requests and to return results, but it can actually be decoupled.</li>
</ul>

This architecture (or similar ones, making use of a main application framework, a worker provider and a message broker) is useful for exposing asynchronous APIs, which is typically necessary whenever it's required that the backend performs longer tasks (from seconds even to minutes or hours). This is the typical situation for all ML applications.
The typical interaction proceeds as follows: 
<ol>
    <li>A client sends an API request to the main endpoint, entering details in the form item_a & item_b, and receives a positive response containing the task id;</li>
    <li>In the background, the broker stores the request (with its id) as "PENDING" and forwards it to the first available worker;</li>
    <li>At all times the client can query another endpoint, e.g. https://host/prediction/task_status/<task_id>, to get the status of its task;</li>
    <li>The worker starts its job, processing the document (the core of the solution is actually performed by the worker);</li>
    <li>At the end of its long task, the worker returns the result to the broker, that changes the status to "SUCCESS";</li>
    <li>Once the client receives a "SUCCESS" status from the status endpoint, it can query another endpoint dedicated to retrieving the result, e.g. https://host/prediction/task_result/<task_id>, obtaining the processed data.</li>
</ol>

In the current solution, we adopted some atypical settings in order to fit it to our requirements, as discussed in the dedicated paragraph.<br>

### Project structure
    .
    ├── flask_app
    │   ├── files/
    │   ├── templates/base.html
    │   ├── Dockerfile
    │   ├── app.py
    │   └── requirements.txt
    ├── ml_worker
        ├── model.pth
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   └── tasks.py
    ├── rabbitmq
    │   ├── advanced.config
    │   ├── Dockerfile
    │   └── rabbitmq.conf
    └── docker-compose.yml

#### flask_app
It contains the exposed API endpoints, described in app.py. All the endpoints are served under /activedocuments/nexans/. The minimal interface to be served is contained in the templates/ folder.<br>
It looks like a classic Flask application, except for the "async_app" variable that encapsulates a Celery(+RabbitMQ broker/backend) setup. The first parameter of the Celery object is the name of the folder containing the worker structure/logic (in this case: 'ml_worker'); please make the necessary changes to the code if you rename it.<br>
The same "async_app" Celery object is called within the /uploader endpoint to deliver the task to the actual worker, with the "send_task" function. The first parameter for send_task is "py task file"."fnc name") and all the parameters are sent as kwargs.<br>
As described in the architecture explanation we also have two more endpoints checking for the task status and retrieving the task result (they both take the task_id as the only parameter).

#### ml_worker
It contains the core of the application, encapsulating the ml model (in the utils/layoutLMutils.py file) and structuring the output data as per the requirements.<br>
Notice the "app" variable encapsulating the same Celery object that was defined in the flask_app, this time taking as the first parameter the name of the python file containing the tasks (in this case: 'tasks'); please make the necessary changes to the code if you rename it.<br>
The only defined task for our use case is "elab_file" (which is the "fnc name" invoked from the /uploader endpoint of Flask). The actual logic of the elaboration is contained in the utilities.<br>
Depending on the parameters specified by the user, the task can also deliver the results on its own using a webhook or the FTP utilities to send the results directly to the client. In this case the client might also never retrieve the results - this requires a specific setting for the RabbitMQ broker to work without failures.

#### rabbitmq
It contains the latest Docker image for RabbitMQ and a couple of extra configuration files, to adapt the solution to our needs.
> advanced.config sets the consumer_timeout to undefined. It means that the client might never retrieve the result for his task. Be careful around this setting because this is typically NOT how you want this architecture to behave! This might open up to DDoS attacks, overloading the backend with requests that are never retrieved by anyone. It was introduced in our use case because we decided the workers should deliver the results through a webhook on their own at the end of their tasks.

#### docker-compose.yml
Configuration file to build all the Docker images above at once, and mount a shared volume for sharing documents (input and output data) from one container to the other. The exposed port is for the Flask application, but there is also a RabbitMQ dashboard available to visually monitor requests and queues. Make sure the ports on the server are open, otherwise you wouldn't be able to access.


## How to install and test locally with Docker
Download or clone this branch of the repository with the method of your choice. E.g., if you have git on your machine:

    git clone 
    
This will download the files in the <b>AsyncArcheitecture</b> folder.<br>
Make sure to have Python and Docker installed on your machine. For instructions on how to do so, I suggest installing either <a href="https://www.anaconda.com/products/individual">Anaconda</a> (full distribution with 250+ packages included, the easiest installation tool available even for Python agnostic users, but on the heavier side) or one of the smaller conda distributions like <a href="https://docs.conda.io/en/latest/miniconda.html">Miniconda</a> (providing only a few packages other than conda and Python, including the package manager pip).
Aside from these suggestions, any Python distribution with a package manager will work fine.<br>
Make sure to have Docker up and running on your machine. For installation and setup, please refer to <a href="https://www.docker.com/products/docker-desktop">Docker</a>.<br>
> If you run Docker on Windows and experience some issues with the following procedures, try to launch Docker as administrator, or refer to any forum like <a href="https://stackoverflow.com/questions/62377865/docker-for-windows-will-not-start">this</a> for troubleshooting.

After cloning the repository, run the following commands:

    cd AsyncArcheitecture
    docker-compose build
    
This will create 3 Docker images called AsyncArcheitecture_flask_app_1, AsyncArcheitecture_ml_worker_1, AsyncArcheitecture_rabbit_1. You can check it either by looking in your Docker desktop client or by running 'docker images'.<br>
Then you will have to run the images:

    docker-compose up
    
Before doing so, make sure the port mapping for flask_app inside docker-compose.yml is set to the port of your choice. If you leave it as it is in our project, it is bound to listen on port 5000.<br>
Test if the procedure was completed correctly by visiting localhost:5000/prediction/upload. It should present you with the minimal interface defined in flask_app/templates/base.html.<br>
By default, Docker tries to load the server certificate and the private key for serving everything under https. You can change this behavior by commenting line 14 and uncommenting line 15 on flask_app Dockerfile:

    CMD gunicorn --bind=0.0.0.0:5000 --timeout=0 app:app
    
When using AWSutils functions .the project looks for AWS credentials in the environment variables. You can either set them in a .env file (within flask_app/) like the following:

    AWS_ACCESS_KEY_ID=your-access-key-id
    AWS_SECRET_ACCESS_KEY=your-secret-access-key
    AWS_BUCKET_NAME=your-s3-bucket
    AWS_REGION=your-chosen-region

or you can feed the environment variables directly to the container in the docker-compose.yml, by adding the following lines in flask_app settings:

    environment:
      - AWS_ACCESS_KEY_ID=your-access-key-id
      - AWS_SECRET_ACCESS_KEY=your-secret-access-key
      - AWS_BUCKET_NAME=your-s3-bucket
      - AWS_DEFAULT_REGION=your-chosen-region


## Endpoints
The base endpoint for all the following is <b>/activedocuments/nexans/</b>.
### /echo/
The /echo/ endpoint is used to test if the webserver is up and running.<br>

Defined return codes:
<ul>
    <li>🟢 200: Success</li>
</ul>

### /upload/
The /upload/ endpoint is used to serve an html minimal interface to let the user upload files. The only verb served at this endpoint is GET.<br>

Defined return codes:
<ul>
    <li>🟢 200: Success</li>
</ul>

### /uploader/
The /uploader/ endpoint is the endpoint actually handling file transfer. It serves only POST requests.<br>
It accepts a body containing:
<ul>
    <li>item_a: Write any item name for eg:TV</li>
    <li>item_b: Write any item name for eg: Samsung</li>
</ul>

Defined return codes:
<ul>
    <li>🟢 200: Success (returns a success message containing the task_id of the request)</li>
    <li>🔴 401: Bad Request (invalid file extension, file not found)</li>
</ul>

### /task_status/<task_id>
The /task_status/<task_id> endpoint is used to check if a task is completed or not. The only verb served at this endpoint is GET.<br>

Defined return codes:
<ul>
    <li>🟢 200: Success (it returns a string in format "Status of the Task &lt;status&gt;", where status can be PENDING, SUCCESS, FAILED)</li>
</ul>

### /task_result/<task_id>
The /task_result/<task_id> endpoint is used to retrieve a completed task results. The only verb served at this endpoint is GET.<br>

Defined return codes:
<ul>
    <li>🟢 200: Success (it returns the string response)</li>
</ul>

![alt text](images/image1.png)

![alt text](images/image2.png)

![alt text](images/image3.png)

![alt text](images/image4.png)

![alt text](images/image5.png)


# References

- [Flask Asynchronous Background Tasks with Celery and Redis](http://allynh.com/blog/flask-asynchronous-background-tasks-with-celery-and-redis/)
- [Video by Soumil Shah](https://www.youtube.com/watch?v=ybftbk_l6iU&t=177s&ab_channel=SoumilShah)
