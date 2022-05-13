#from bcrypt import methods
import email
from unicodedata import category
from app import app, db
from flask import render_template, redirect, flash, request, url_for
from flask_login import current_user, login_user, login_required, logout_user
from app.models import User, Role, Permission, Product, Cooperative, Post, Comment
from app.picture_handler import add_product_pic
from app.forms import LoginForm, RegistrationForm, EditUserForm, EditAgentForm, \
    ProductForm, UpdateProductForm, CooperativeForm, PurchaseForm, SellingForm, PostForm, CommentForm



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/market', methods=['POST', 'GET'])
@login_required
def market():

    products = Product.query.all()

    purchase_form = PurchaseForm()
    selling_form = SellingForm()

    if request.method == 'POST':

        purchased_product = request.purchase_form.get('purchased_product')
        purchased_object = Product.query.filter_by(product_name=purchased_product).first()

        if purchased_object:
            if current_user.can_purchase(purchased_object):
                purchased_object.buy(current_user)               
                current_user.points = current_user.add_points(purchased_object)
                flash(f'Success! You purchased {purchased_object.product_name} for \
                      {purchased_object.price}NGN', category='success')
            else:
                flash(f'You do not have enough funds to purchase {purchased_object}', category='danger')

        sold_product = request.selling_form.get('sold_product')
        sold_object = Product.query.filter_by(product_name=sold_product).first()
        if sold_object:
            if current_user.can_sell(sold_object):
                sold_object.sell(current_user)
                current_user.points = current_user.add_points(sold_object)
                flash(f'You have successfully sold {sold_object.product_name} for \
                     {sold_object.price}NGN', category='success')
            else:
                flash(f'Something is wrong with selling {sold_object.product_name}', category='danger')
        
        return redirect(url_for('market'))

    if request.method == 'GET':
        products = Product.query.filter_by(owner_supplier=None)
        owned_products = Product.query.filter_by(owner_supplier=current_user.id)
        return render_template('market.html', products=products, 
                                purchase_form=purchase_form,
                                selling_form=selling_form, 
                                owned_products=owned_products)


@app.route('/register', methods=['POST', 'GET'])
def register():

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data.lower(),
                    password=form.password.data,
                    firstname=form.firstname.data,
                    lastname=form.lastname.data,
                    mobile_no=form.mobile_no.data,
                    location=form.location.data)
        db.session.add(user)
        db.session.commit()
        flash(f'Congratulations! You have successfully registered with TingoApp.', category='success')
        return redirect(url_for('login'))

    if form.errors != {}:
        for err_msg in form.errors.values():
            flash(f'There was an error with creating a user: {err_msg}', category='danger')

    return render_template('register.html', form=form)


@app.route('/login', methods=['POSt', 'GET'])
def login():

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.verify_password(form.password.data):
            login_user(user)
            flash(f'Success! You are logged in as {user.firstname}', category='success')
            next = request.args.get('next')
            if next is None or not next.startswith('/'):
                next = url_for('index')
            return redirect(next)
        else:
            flash('Invalid email or password.', category='danger')
    return render_template('login.html', form=form)

#, form.remember_me.data

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out!', category='info')
    return redirect(url_for('index'))


@app.route('/add_product', methods=['GET','POST'])
@login_required
def add_product():

    form = ProductForm()
    if form.validate_on_submit():

        product = Product(product_name=form.product_name.data,
                          product_type=form.product_type.data,
                          product_variety=form.product_variety.data,
                          location=form.location.data)

        if product.owner_supplier is None:
            product.owner_supplier = current_user.firstname

        db.session.add(product)
        db.session.commit()
        flash('A new Product has been added to the MarketPlace!', category='success')

        return redirect(url_for('.farmer'))

    page = request.args.get('page', 1, type=int)
    pagination = Product.query.order_by(Product.product_name).paginate(
        page, per_page=20, error_out=False) #current_app.config['TINGO_PRODUCTS_PER_PAGE']
    products = pagination.items

    return render_template('marketpage.html', form=form, products=products,
                            pagination=pagination)



@login_required
@app.route('/product/<int:id>', methods=['GET','POST'])
def update_product(id):

    product = Product.query.get_or_404(id)
    form = UpdateProductForm()
    if form.validate_on_submit():

        if form.picture.data:
            product_name = product.product_name
            pic = add_product_pic(form.picture.data,product_name)
            product.product_image = pic

        product.product_name = form.product_name.data
        product.product_type = form.product_type.data
        product.product_variety = form.product_variety.data
        product.location = form.location.data
        product.price = form.price.data
        product.description = form.description.data

        db.session.commit()
        flash('Product Information Updated!')
        return redirect(url_for('user'))

    product_image = url_for('static',filename='product_pics/'+product.product_image)
    return render_template('edit_product.html',product_image=product_image,form=form)


@app.route('/delete_product/<int:id>', methods=['GET','POST'])
@login_required
def delete_product(id):

    product = Product.query.get_or_404(id)

    db.session.delete(product)
    db.session.commit()
    flash('The Product has been deleted!')
    return redirect(url_for('.user', id=product.id))


@app.route('/user/<firstname>')
def user(firstname):
    user = User.query.filter_by(firstname=firstname).first_or_404()
    page = request.args.get('page', 1, type=int)
    products_pagination = user.products.order_by(Product.timestamp.desc()).paginate(
        page, per_page=20, error_out=False) #current_app.config['PRODUCTS_PER_PAGE']
    products = products_pagination.items
    users_pagination = user.farmers.order_by(User.id.asc()).paginate(
        page, per_page=20, error_out=False) #current_app.config['FARMERS_PER_PAGE'
    if current_user.can(Permission.REGISTER):
        farmers = users_pagination.items
    return render_template('user.html', user=user, products=products, farmers=farmers,
                           products_pagination=products_pagination,
                           users_pagination=users_pagination)


@app.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditUserForm()
    form.cooperative.choices = [(cooperative.id, cooperative.name) for cooperative in Cooperative.query.all()]
    if form.validate_on_submit():
        current_user.firstname = form.firstname.data
        current_user.lastname = form.lastname.data
        current_user.date_of_birth = form.date_of_birth.data
        current_user.location = form.location.data
        current_user.state_of_origin = form.state_of_origin.data
        current_user.country = form.country.data
        current_user.about_me = form.about_me.data
        current_user.cooperative = form.cooperative.data
        db.session.add(current_user._get_current_object())
        db.session.commit()
        flash('Your profile has been updated.')
        return redirect(url_for('.farmer', firstname=current_user.firstname))
    form.firstname.data = current_user.firstname
    form.lastname.data = current_user.lastname
    form.date_of_birth.date = current_user.date_of_birth
    form.location.data = current_user.location
    form.state_of_origin.data = current_user.state_of_origin
    form.country.data = current_user.country
    form.about_me.data = current_user.about_me
    form.cooperative.data = current_user.cooperative
    return render_template('edit_profile.html', form=form)


@app.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_profile_user(id):
    agent = User.query.get_or_404(id)
    form = EditAgentForm(user=user)
    form.role.choices = [(role.id, role.name) for role in Role.query.all()]
    if form.validate_on_submit():
        user.email = form.email.data
        user.role = Role.query.get(form.role.data)
        user.firstname = form.firstname.data
        user.lastname = form.lastname.data
        user.confirmed = form.confirmed.data
        user.date_of_birth = form.date_of_birth.data
        user.location = form.location.data
        user.state_of_origin = form.state_of_origin.data
        user.country = form.country.data
        user.about_me = form.about_me.data
        user.role = form.role.data
        db.session.add(user)
        db.session.commit()
        flash('The profile has been updated.')
        return redirect(url_for('.user', firstname=user.firstname))
    form.email.data = user.email
    form.firstname.data = user.firstname
    form.lastname.data = user.lastname
    form.confirmed.data = user.confirmed
    form.date_of_birth.data = user.date_of_birth
    form.location.data = user.location
    form.state_of_origin = user.state_of_origin
    form.country = user.country
    form.about_me.data = user.about_me
    form.role.data = user.role
    return render_template('edit_profile.html', form=form, user=user)


@login_required
@app.route('/admin', methods=['POST', 'GET'])
def admin():
    pass


@app.route('/forum', methods=['POST', 'GET'])
def forum():
    pass


@app.route('/post', methods=['POST', 'GET'])
def post():
    pass

                            





