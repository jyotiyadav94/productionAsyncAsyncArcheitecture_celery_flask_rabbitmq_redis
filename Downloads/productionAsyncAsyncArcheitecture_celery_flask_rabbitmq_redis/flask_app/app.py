from flask import Flask, render_template, request, redirect, make_response, send_file, Blueprint
from flask import Flask
from celery import Celery
import os

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.config['JSON_SORT_KEYS'] = False
async_app = Celery('tasks', 
                    broker='amqp://admin:mypass@rabbit:5672', 
                    backend='rpc://')

# Define the blueprint
bp = Blueprint('prediction', __name__, template_folder='templates')
@bp.route('/')
def base():
    return {'error': 'no endpoint specified'}, 400


@bp.route('/echo')
def echo():
    return "Hello! FINALMENTE!", 200


@bp.route('/upload')
def upload():
    headers = {'Content-Type': 'text/html'}
    return make_response(render_template('base.html'), 200, headers)


@bp.route('/uploader', methods = ['POST'])
def async_uploader():
    app.logger.info("Invoking Method ")
    item_a = request.form.get('item_a', "Jyoti")
    item_b = request.form.get('item_b', 'Yadav')
    #                        queue name in task folder.function name
    r = async_app.send_task('tasks.elab_file', kwargs={'item_a': item_a, 'item_b': item_b})
    app.logger.info(r.backend)
    return {'task_id': r.id}, 200

@bp.route('/task_status/<task_id>')
def get_status(task_id):
    status = async_app.AsyncResult(task_id, app=async_app)
    print("Invoking Method to get task status")
    print(task_id)
    print(status)
    return "Status of the Task " + str(status.state)

@bp.route('/task_result/<task_id>')
def task_result(task_id):
    result = async_app.AsyncResult(task_id).result
    print("result",result)
    print("Invoking Method to get task result")
    return "Result of the Task " + str(result)

# Register the blueprint with the Flask application
app.register_blueprint(bp, url_prefix='/prediction')