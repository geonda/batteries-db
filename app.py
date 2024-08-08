import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, FileField, SubmitField
from wtforms.validators import DataRequired
from flask import send_from_directory
from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()])

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///materials.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'  # Folder to save uploaded files
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit upload size to 16MB
app.secret_key = 'your_secret_key'  # Needed for CSRF protection

db = SQLAlchemy(app)
api = Api(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Redirect to login if not logged in

api_keys = {
    'test':'eyJhbGciOiJIUzUxMiIsImlhdCI6MTcyMzEyMzk5MSwiZXhwIjoxNzIzMTI3NTkxfQ.eyJ1c2VybmFtZSI6InRlc3QifQ.eptec4pgYzsdi72Ma4eG6Z9OqHWIzNyegt3dxbVl6_Pqr4Aak0DJBiVmCoHY3ZaINdu4v1HH-3-61EwCgjaPsw'
}

# Define the Material model
class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    quantity = db.Column(db.Integer, nullable=False)
    filename = db.Column(db.String(100), nullable=True)  # To store the uploaded file name

    def __repr__(self):
        return f'<Material {self.name}>'
# Define the User model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

# Create the database and the table
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Decorator to check API key
def require_api_key(func):
    def wrapper(*args, **kwargs):
        username = request.headers.get('Username')
        api_key = request.headers.get('API-Key')
        if username not in api_keys or api_keys[username] != api_key:
            return jsonify({'error': 'Unauthorized access'}), 401

        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('register'))

        new_user = User(username=username, password=password)  # Note: In production, hash the password!
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# API Resource for Materials
class MaterialResource(Resource):
    @require_api_key
    def get(self):
        materials = Material.query.all()
        return jsonify([{
            'id': material.id,
            'name': material.name,
            'description': material.description,
            'quantity': material.quantity,
            'filename': material.filename
        } for material in materials])
    
    @require_api_key
    def post(self):
        print(request)
        data = request.form
        name = data.get('name')
        description = data.get('description')
        quantity = data.get('quantity')
        file = request.files.get('file')

        # Save the file if it exists
        filename = None
        if file:
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        new_material = Material(name=name, description=description, quantity=int(quantity), filename=filename)
        db.session.add(new_material)
        db.session.commit()

        logging.info(f'Added material: {new_material.name}, Quantity: {new_material.quantity}, File: {filename}')
        # print(jsonify({'message': 'Material added successfully', 'id': new_material.id}))
        return {'message': 'Material added successfully', 'id': new_material.id}, 201

class ApiKeyResource(Resource):
    def post(self):
        username = current_user.username
        if username in api_keys:
            return {'api_key': api_keys[username]}, 202

        s = Serializer(app.config['SECRET_KEY'], expires_in=3600*24*360)  # Key expires in 1 hour
        api_key = s.dumps({'username': username}).decode('utf-8')
        print(api_keys)
        print(username)
        api_keys[username] = api_key
        print(api_keys)
        return {'api_key': api_key}, 200

    
# Create a form class for materials
class MaterialForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    quantity = IntegerField('Quantity', validators=[DataRequired()])
    file = FileField('Upload File')
    submit = SubmitField('Add Material')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:  # Simple password check
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')


@app.route('/api/download/<int:material_id>', methods=['GET'])
def download_file(material_id):
    material = Material.query.get(material_id)
    if material and material.filename:
        return send_from_directory(app.config['UPLOAD_FOLDER'], material.filename, as_attachment=True)
    else:
        return jsonify({'error': 'File not found or does not exist'}), 404
    
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    search_query = request.args.get('search', '')
    if search_query:
        materials = Material.query.filter(Material.name.ilike(f'%{search_query}%')).all()
    else:
        materials = Material.query.all()
    return render_template('index.html', materials=materials, search_query=search_query)


@app.route('/add', methods=['GET', 'POST'])
def add_material():
    form = MaterialForm()
    if form.validate_on_submit():
        name = form.name.data
        description = form.description.data
        quantity = form.quantity.data
        file = form.file.data

        # Save the file if it exists
        filename = None
        if file:
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        new_material = Material(name=name, description=description, quantity=quantity, filename=filename)
        db.session.add(new_material)
        db.session.commit()

        # Log the action
        logging.info(f'Added material: {new_material.name}, Quantity: {new_material.quantity}, File: {filename}')
        return redirect(url_for('index'))

    return render_template('add_material.html', form=form)

@app.route('/delete/<int:material_id>')
def delete_material(material_id):
    material = Material.query.get(material_id)
    if material:
        db.session.delete(material)
        db.session.commit()
        logging.info(f'Deleted material: {material.name}')
    return redirect(url_for('index'))

@app.route('/edit/<int:material_id>', methods=['GET', 'POST'])
def edit_material(material_id):
    material = Material.query.get(material_id)
    form = MaterialForm(obj=material)
    if form.validate_on_submit():
        material.name = form.name.data
        material.description = form.description.data
        material.quantity = form.quantity.data
        file = form.file.data

        # Save the file if it exists
        if file:
            material.filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], material.filename))

        db.session.commit()

        # Log the action
        logging.info(f'Updated material: {material.name}, Quantity: {material.quantity}, File: {material.filename}')
        return redirect(url_for('index'))

    return render_template('edit_material.html', form=form, material=material)

@app.route('/uploads/<filename>')
def uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/generate_key', methods=['POST'])
def generate_key():
    username = request.form.get('username')
    print(username)
    if username in api_keys:
        return jsonify({'error': 'API key already exists for this user'}), 400

    s = Serializer(app.config['SECRET_KEY'], expires_in=3600)  # Key expires in 1 hour
    api_key = s.dumps({'username': username}).decode('utf-8')
    api_keys[username] = api_key
    print(api_keys)
    return jsonify({'api_key': api_key}), 200

api.add_resource(MaterialResource, '/api/materials')
api.add_resource(ApiKeyResource, '/api/api_keys')


@app.route('/api/verify_key', methods=['POST'])
def verify_key():
    api_key = request.form.get('api_key')
    for username, key in api_keys.items():
        try:
            s = Serializer(app.config['SECRET_KEY'])
            data = s.loads(key)
            if data['username'] == username:
                return jsonify({'message': 'API key is valid'}), 200
        except:
            pass
    return jsonify({'error': 'Invalid API key'}), 401

if __name__ == '__main__':
    # Create the uploads folder if it doesn't exist
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
