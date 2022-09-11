from flask import Blueprint, render_template

feed_importer = Blueprint('feed_importer', __name__, template_folder='templates', static_folder='static',
                          url_prefix='/feed-importer')


@feed_importer.route('/', methods=['GET'])
def index():
    return render_template('feed_importer.html')

@feed_importer.route('/load/',methods=['POST'])
def load():
    return render_template('feed_importer.html')
