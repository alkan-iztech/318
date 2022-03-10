from flask import Flask, render_template, request, session, make_response, jsonify, redirect
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from recom import process_csv, get_combined, get_cos_sim, recommend
import os
from validators import validate_user_data
from numpy import savez_compressed, load
import shutil

app = Flask(__name__)
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = "filesystem"
app.debug = True
Session(app)

BOOK_RECOM_ENV = os.environ.get("THREE_ONE_EIGHT_ENV")
if BOOK_RECOM_ENV == 'prod':
    app.debug = False
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("JAWSDB_URL")
else:
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/three_one_eight'

db = SQLAlchemy(app)

@app.before_first_request
def setup():
    db.create_all()
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password = password

class App(db.Model):
    __tablename__ = 'apps'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    first_item_id = db.Column(db.Integer)

    def __init__(self, name, user_id, first_item_id):
        self.name = name
        self.user_id = user_id
        self.first_item_id = first_item_id
    
    def __repr__(self) -> str:
        return str(self.id) + " " + self.name
class AppItem(db.Model):
    __tablename__ = 'app_items'
    id = db.Column(db.Integer, primary_key=True)
    concat_data = db.Column(db.String(300), nullable=False)
    app_id = db.Column(db.Integer, db.ForeignKey('apps.id'))
    # cos_sim_row = db.Column(db.LargeBinary)
    
    def __init__(self, concat_data, app_id) -> None:
        self.concat_data = concat_data
        self.app_id = app_id

    def __repr__(self) -> str:
        return str(self.id) + " ## " + str(self.app_id) + " ## " + self.concat_data

df = None
cos_sim = None

try:
    user = User('ADMIN', 'admin@gmail.com', 'admin')
    db.session.add(user)
    db.session.commit()
    print('user is created')
except:
    print('user is already created')

apps_directory = os.path.join(os.getcwd(), 'apps')
print('apps_directory:', apps_directory)

def create_directory_if_not_exists(path):
    if not os.path.isdir(path):
        os.mkdir(path)

###########################
########### API ###########
###########################
@app.route('/')
def home():
    return make_response({'home': 'HOME'}, 200)

@app.route('/signup', methods=['POST'])
def signup():
    try:
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password_confirm = request.form['password-confirm']
        validation_result = validate_user_data(db, User, username, email, password, password_confirm)
        if validation_result == '':
            data = User(username, email, password)
            db.session.add(data)
            db.session.commit()
            return custom_message(data.id, 200)
        return custom_message({'validation': validation_result}, 404)
    except Exception as e:
        return custom_message({'message': e}, 404)

@app.route('/login', methods=['POST'])
def login():
    try:
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            return custom_message(user.id, 200)
        else:
            return custom_message('Incorrect email or password', 404)

    except Exception as e:
        return custom_message(e, 404)

@app.route('/logout', methods=['GET'])
def logout():
    return custom_message('Logged out', 200)

@app.route('/csv', methods=['GET', 'POST'])
def csv():
    if request.method == 'GET':
        return render_template('upload_csv.html')
    else:
        create_directory_if_not_exists(apps_directory)
        print(request.form)
        file = request.files['uploadFile']
        app_title = request.form['app-title']
        delimiter = request.form['delimiter']
        user_id = request.form['user-id']
        file_df = process_csv(file, delimiter)
        print(file_df.tail())
        print('###')
        # file.save(os.getcwd() + '/alkan.csv')
        # breakpoint()

        new_app = App(app_title, user_id, -1)
        db.session.add(new_app)
        db.session.flush()
        new_app_path = os.path.join(apps_directory, f'app_{new_app.id}')
        create_directory_if_not_exists(new_app_path)

        combined = get_combined(file_df)
        first = AppItem(combined[0], new_app.id)
        db.session.add(first)
        db.session.flush()

        new_app.first_item_id = first.id
        db.session.add(new_app)
        # save each row as AppItem to db
        for i in range(1, len(combined)):
            item = AppItem(combined[i], new_app.id)
            db.session.add(item)
        db.session.commit()

        ###################
        ## EXPORT COSIMs ##
        ###################
        cos_sim = get_cos_sim(file_df, combined)
        for i in range(len(cos_sim)):
            filename = f"row_{i}.npz"
            savez_compressed(os.path.join(new_app_path, filename), cos_sim[i])
            # savez_compressed(os.path.abspath('./apps/' + filename), cos_sim[i])

        return custom_message({'id': new_app.id, 'name': new_app.name}, 200)

@app.route('/get-recom', methods=['GET', 'POST'])
def get_recom():
    if request.method == 'GET':
        return render_template('recom.html')
    name = request.form['name']
    app_id = int(request.form['app-id'])
    print('boom:', AppItem.query.filter(AppItem.concat_data.startswith(name)).first())
    app_item = AppItem.query.filter(
        AppItem.concat_data.startswith(name),
        AppItem.app_id == app_id
        ).first()
    app = App.query.filter(App.id == app_id).first()
    if not app_item or not app:
        print('app_item', app_item)
        print('app', app)
        return custom_message({'msg': 'Couldn\'t find item'}, 404)
    
    app_path = os.path.join(apps_directory, f'app_{app.id}')
    filename = f"row_{app_item.id - app.first_item_id}.npz"
    row = load(os.path.join(app_path, filename))['arr_0']
    item_ids = list(map(lambda i: i + app.first_item_id, recommend(row, 5)))
    items = AppItem.query.filter(AppItem.id.in_(item_ids)).all()
    print(items)
    items_map = {}
    for item in items:
        item_json = {}
        item_json['app_id'] = item.app_id
        item_json['data'] = item.concat_data
        items_map[item.id] = item_json
    return custom_message(items_map, 200)

@app.route('/clear')
def clear():
    AppItem.query.delete()
    App.query.delete()
    # User.query.delete()
    db.session.commit()
    shutil.rmtree(apps_directory)
    return custom_message({'msg': 'Cleared'}, 200)

@app.route('/app/<int:id>')
def get_app(id):
    the_app = App.query.filter(App.id == id).first()
    if the_app:
        return custom_message({'id': the_app.id, 'name': the_app.name}, 200)
    else:
        return custom_message({'msg': f'App with {id} is not found.'}, 404)

@app.route('/app/<int:id>/update', methods=['POST'])
def update_app(id):
    new_name = request.form['name']
    the_app = App.query.filter(App.id == id).first()
    if the_app:
        the_app.name = new_name
        db.session.commit()
        return custom_message({'id': the_app.id, 'name': the_app.name}, 200)
    else:
        return custom_message({'msg': f'App with {id} is not found.'}, 404)

@app.route('/app/<int:id>/delete', methods=['POST'])
def delete_app(id):
    the_app = App.query.filter(App.id == id).first()
    if not the_app:
        return custom_message({'msg': f'App with {id} is not found.'}, 404)
    else:
        # delete AppItems that belongs to this app first
        AppItem.query.filter(AppItem.app_id == the_app.id).delete()
        # delete this app
        App.query.filter(App.id == id).delete()
        # delete folder from apps
        app_directory = os.path.join(apps_directory, f'app_{id}')
        if os.path.isdir(app_directory):
            shutil.rmtree(app_directory)
        db.session.commit()
        return custom_message({'id': the_app.id, 'name': the_app.name}, 200)

def custom_message(message, status_code): 
    return make_response(jsonify(message), status_code)

if __name__ == '__main__':
    app.run()
