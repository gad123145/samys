from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, and_
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename
import pandas as pd
import tempfile

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# إنشاء مجلد الصور إذا لم يكن موجوداً
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# نموذج المستخدم
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='agent')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# نموذج العميل
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)  # تغيير إلى nullable=True
    phone = db.Column(db.String(20), nullable=True)
    facebook_id = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='new_client')
    notes = db.Column(db.Text, nullable=True)
    next_follow_up = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_status_display(self):
        status_dict = {
            'new_client': 'عميل جديد',
            'potential_client': 'عميل محتمل',
            'interested_client': 'عميل مهتم',
            'responded': 'تم الرد',
            'no_response': 'لم يتم الرد',
            'appointment_set': 'تم تحديد موعد',
            'post_meeting': 'ما بعد الاجتماع',
            'booked': 'تم الحجز',
            'cancelled': 'تم الإلغاء',
            'sold': 'تم البيع',
            'postponed': 'مؤجل',
            'resale': 'إعادة البيع'
        }
        return status_dict.get(self.status, self.status)

    def get_status_color(self):
        color_map = {
            'new_client': 'info',
            'potential_client': 'secondary',
            'interested_client': 'success',
            'responded': 'warning',
            'no_response': 'danger',
            'appointment_set': 'success',
            'post_meeting': 'primary',
            'booked': 'success',
            'cancelled': 'danger',
            'sold': 'success',
            'postponed': 'warning',
            'resale': 'primary'
        }
        return color_map.get(self.status, 'secondary')

# نموذج التذكرة
class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='open')
    priority = db.Column(db.String(20), default='medium')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    agent_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# نموذج العقار
class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    details = db.Column(db.Text)
    owner_phone = db.Column(db.String(20))
    images = db.Column(db.JSON)  # لتخزين مسارات الصور
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# نموذج الشركة المطورة
class DeveloperCompany(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    license_number = db.Column(db.String(50))
    description = db.Column(db.Text)
    logo = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_customer_counts():
    try:
        counts = {
            'new_customers': Customer.query.filter_by(status='عميل جديد').count(),
            'potential_customers': Customer.query.filter_by(status='عميل محتمل').count(),
            'interested_customers': Customer.query.filter_by(status='عميل مهتم').count(),
            'responded': Customer.query.filter_by(status='تم الرد').count(),
            'no_response': Customer.query.filter_by(status='لم يتم الرد').count(),
            'appointment_set': Customer.query.filter_by(status='تم تحديد موعد').count(),
            'post_meeting': Customer.query.filter_by(status='ما بعد الاجتماع').count(),
            'booked': Customer.query.filter_by(status='تم الحجز').count(),
            'cancelled': Customer.query.filter_by(status='تم الإلغاء').count(),
            'sold': Customer.query.filter_by(status='تم البيع').count(),
            'postponed': Customer.query.filter_by(status='مؤجل').count(),
            'resale': Customer.query.filter_by(status='إعادة البيع').count()
        }
        return dict(customer_counts=counts)
    except:
        # في حالة وجود أي خطأ، نعيد قاموس فارغ
        return dict(customer_counts={})

@app.route('/')
@login_required
def index():
    try:
        # Get search parameters
        query = request.args.get('query', '').strip()
        status = request.args.get('status', '').strip()
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        sort = request.args.get('sort', 'created_desc')

        # Base query
        customers_query = Customer.query

        # Apply search filters
        filters = []
        if query:
            filters.append(or_(
                Customer.name.ilike(f'%{query}%'),
                Customer.email.ilike(f'%{query}%'),
                Customer.phone.ilike(f'%{query}%')
            ))
        
        if status:
            filters.append(Customer.status == status)
        
        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d')
                filters.append(Customer.created_at >= date_from)
            except ValueError:
                flash('تنسيق تاريخ البداية غير صحيح', 'warning')
        
        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d')
                # Add one day to include the entire end date
                date_to = date_to + timedelta(days=1)
                filters.append(Customer.created_at < date_to)
            except ValueError:
                flash('تنسيق تاريخ النهاية غير صحيح', 'warning')

        # Apply all filters
        if filters:
            customers_query = customers_query.filter(and_(*filters))

        # Apply sorting
        if sort == 'created_asc':
            customers_query = customers_query.order_by(Customer.created_at.asc())
        elif sort == 'created_desc':
            customers_query = customers_query.order_by(Customer.created_at.desc())
        elif sort == 'name_asc':
            customers_query = customers_query.order_by(Customer.name.asc())
        elif sort == 'name_desc':
            customers_query = customers_query.order_by(Customer.name.desc())

        # Get customers and calculate statistics
        customers = customers_query.all()
        total_customers = Customer.query.count()

        # Calculate statistics
        stats = {
            'new_clients': Customer.query.filter_by(status='new_client').count(),
            'potential_clients': Customer.query.filter_by(status='potential_client').count(),
            'interested_clients': Customer.query.filter_by(status='interested_client').count(),
            'responded': Customer.query.filter_by(status='responded').count(),
            'no_response': Customer.query.filter_by(status='no_response').count(),
            'appointment_set': Customer.query.filter_by(status='appointment_set').count(),
            'post_meeting': Customer.query.filter_by(status='post_meeting').count(),
            'booked': Customer.query.filter_by(status='booked').count(),
            'cancelled': Customer.query.filter_by(status='cancelled').count(),
            'sold': Customer.query.filter_by(status='sold').count(),
            'postponed': Customer.query.filter_by(status='postponed').count(),
            'resale': Customer.query.filter_by(status='resale').count()
        }

        # Calculate percentages
        percentages = {
            status: round((count / total_customers * 100) if total_customers > 0 else 0, 1)
            for status, count in stats.items()
        }

        # Get upcoming follow-ups for next 7 days
        upcoming_followups = Customer.query.filter(
            and_(
                Customer.next_follow_up >= datetime.now(),
                Customer.next_follow_up <= datetime.now() + timedelta(days=7)
            )
        ).order_by(Customer.next_follow_up.asc()).limit(5).all()

        # Get overdue follow-ups
        overdue_followups = Customer.query.filter(
            Customer.next_follow_up < datetime.now()
        ).order_by(Customer.next_follow_up.desc()).limit(5).all()

        return render_template('index.html',
                            customers=customers,
                            stats=stats,
                            percentages=percentages,
                            upcoming_followups=upcoming_followups,
                            overdue_followups=overdue_followups,
                            now=datetime.now())

    except Exception as e:
        flash(f'حدث خطأ: {str(e)}', 'error')
        return render_template('index.html', 
                            customers=[],
                            stats={},
                            percentages={},
                            upcoming_followups=[],
                            overdue_followups=[],
                            now=datetime.now())

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # التحقق من عدم وجود المستخدم مسبقاً
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('اسم المستخدم موجود بالفعل')
            return redirect(url_for('register'))
            
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('البريد الإلكتروني مستخدم بالفعل')
            return redirect(url_for('register'))
        
        # إنشاء مستخدم جديد
        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('تم إنشاء الحساب بنجاح! يمكنك الآن تسجيل الدخول')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.password == password:
            login_user(user)
            flash('تم تسجيل الدخول بنجاح!')
            return redirect(url_for('dashboard'))
            
        flash('اسم المستخدم أو كلمة المرور غير صحيحة')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('تم تسجيل الخروج بنجاح')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    tickets = Ticket.query.all()
    return render_template('dashboard.html', tickets=tickets)

@app.route('/tickets/new', methods=['GET', 'POST'])
@login_required
def new_ticket():
    if request.method == 'POST':
        ticket = Ticket(
            subject=request.form.get('subject'),
            description=request.form.get('description'),
            customer_id=request.form.get('customer_id'),
            agent_id=current_user.id
        )
        db.session.add(ticket)
        db.session.commit()
        return redirect(url_for('dashboard'))
    customers = Customer.query.all()
    return render_template('new_ticket.html', customers=customers)

@app.route('/customers')
@login_required
def customers():
    # الحصول على معايير التصفية
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('search', '')
    
    # الحصول على عدد العناصر لكل صفحة
    per_page = int(request.args.get('per_page', 10))
    if per_page not in [10, 25, 50, 100, 500]:
        per_page = 10
    
    # الحصول على رقم الصفحة الحالية
    page = int(request.args.get('page', 1))
    
    # بناء الاستعلام
    query = Customer.query
    
    # تطبيق الفلتر حسب الحالة
    if status_filter != 'all':
        query = query.filter(Customer.status == status_filter)
    
    # تطبيق البحث
    if search_query:
        search = f"%{search_query}%"
        query = query.filter(
            db.or_(
                Customer.name.ilike(search),
                Customer.email.ilike(search),
                Customer.phone.ilike(search),
                Customer.facebook_id.ilike(search)
            )
        )
    
    # الحصول على إجمالي عدد العملاء
    total_customers = query.count()
    
    # تطبيق الترتيب والصفحات
    customers = query.order_by(Customer.created_at.desc()).paginate(
        page=page, 
        per_page=per_page,
        error_out=False
    )
    
    # حساب إجمالي عدد الصفحات
    total_pages = (total_customers + per_page - 1) // per_page
    
    return render_template(
        'customers.html',
        customers=customers,
        status_filter=status_filter,
        search_query=search_query,
        current_page=page,
        total_pages=total_pages,
        per_page=per_page,
        total_customers=total_customers
    )

@app.route('/customer/<int:id>', methods=['GET', 'POST'])
@login_required
def customer_details(id):
    customer = Customer.query.get_or_404(id)
    if request.method == 'POST':
        customer.name = request.form.get('name')
        customer.email = request.form.get('email')
        customer.phone = request.form.get('phone')
        customer.status = request.form.get('status')
        customer.notes = request.form.get('notes')
        next_follow_up = request.form.get('next_follow_up')
        if next_follow_up:
            customer.next_follow_up = datetime.strptime(next_follow_up, '%Y-%m-%d')
        db.session.commit()
        flash('تم تحديث بيانات العميل بنجاح')
        return redirect(url_for('customer_details', id=id))
    return render_template('customer_details.html', customer=customer)

@app.route('/customer/new', methods=['GET', 'POST'])
@login_required
def new_customer():
    if request.method == 'POST':
        customer = Customer(
            name=request.form['name'],
            email=request.form['email'],
            phone=request.form['phone'],
            facebook_id=request.form['facebook_id'],
            status=request.form['status'],
            notes=request.form['notes']
        )
        
        next_follow_up = request.form['next_follow_up']
        if next_follow_up:
            customer.next_follow_up = datetime.strptime(next_follow_up, '%Y-%m-%d')
        
        try:
            db.session.add(customer)
            db.session.commit()
            flash('تم إضافة العميل بنجاح!', 'success')
            return redirect(url_for('customers'))
        except Exception as e:
            db.session.rollback()
            flash('حدث خطأ أثناء إضافة العميل.', 'danger')
            return redirect(url_for('new_customer'))
            
    return render_template('new_customer.html')

@app.route('/edit_customer/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    
    if request.method == 'POST':
        customer.name = request.form['name']
        customer.email = request.form['email'] if request.form['email'] else None
        customer.phone = request.form['phone'] if request.form['phone'] else None
        customer.facebook_id = request.form['facebook_id'] if request.form['facebook_id'] else None
        customer.status = request.form['status']
        customer.notes = request.form['notes'] if request.form['notes'] else None
        
        try:
            db.session.commit()
            flash('تم تحديث بيانات العميل بنجاح', 'success')
            return redirect(url_for('customers'))
        except Exception as e:
            db.session.rollback()
            flash('حدث خطأ أثناء تحديث بيانات العميل', 'danger')
            return redirect(url_for('edit_customer', id=id))
    
    return render_template('edit_customer.html', customer=customer)

@app.route('/delete_customer/<int:id>')
@login_required
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    try:
        db.session.delete(customer)
        db.session.commit()
        flash('تم حذف العميل بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ أثناء حذف العميل', 'danger')
    
    return redirect(url_for('customers'))

@app.route('/delete_customers', methods=['POST'])
@login_required
def delete_customers():
    customer_ids = request.form.getlist('customer_ids[]')
    if customer_ids:
        try:
            Customer.query.filter(Customer.id.in_(customer_ids)).delete(synchronize_session=False)
            db.session.commit()
            flash('تم حذف العملاء المحددين بنجاح', 'success')
        except Exception as e:
            db.session.rollback()
            flash('حدث خطأ أثناء حذف العملاء', 'error')
    return redirect(url_for('customers'))

# وظائف العقارات
@app.route('/properties')
@login_required
def properties():
    properties = Property.query.all()
    return render_template('properties/index.html', properties=properties)

@app.route('/properties/add', methods=['GET', 'POST'])
@login_required
def add_property():
    if request.method == 'POST':
        # معالجة الصور
        images = []
        if 'images' in request.files:
            for image in request.files.getlist('images'):
                if image and allowed_file(image.filename):
                    filename = secure_filename(image.filename)
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    images.append(filename)

        # إنشاء عقار جديد
        property = Property(
            name=request.form['name'],
            location=request.form['location'],
            price=float(request.form['price']),
            details=request.form['details'],
            owner_phone=request.form['owner_phone'],
            images=images
        )
        db.session.add(property)
        db.session.commit()
        flash('تم إضافة العقار بنجاح', 'success')
        return redirect(url_for('properties'))

    return render_template('properties/add.html')

@app.route('/properties/<int:id>')
@login_required
def view_property(id):
    property = Property.query.get_or_404(id)
    return render_template('properties/view.html', property=property)

@app.route('/properties/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_property(id):
    property = Property.query.get_or_404(id)
    if request.method == 'POST':
        property.name = request.form['name']
        property.location = request.form['location']
        property.price = float(request.form['price'])
        property.details = request.form['details']
        property.owner_phone = request.form['owner_phone']

        # معالجة الصور الجديدة
        if 'images' in request.files:
            new_images = []
            for image in request.files.getlist('images'):
                if image and allowed_file(image.filename):
                    filename = secure_filename(image.filename)
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    new_images.append(filename)
            if new_images:
                property.images = property.images + new_images if property.images else new_images

        db.session.commit()
        flash('تم تحديث العقار بنجاح', 'success')
        return redirect(url_for('view_property', id=id))

    return render_template('properties/edit.html', property=property)

@app.route('/properties/<int:id>/delete', methods=['POST'])
@login_required
def delete_property(id):
    property = Property.query.get_or_404(id)
    
    # حذف الصور من المجلد
    if property.images:
        for image in property.images:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image))
            except:
                pass

    db.session.delete(property)
    db.session.commit()
    flash('تم حذف العقار بنجاح', 'success')
    return redirect(url_for('properties'))

# وظائف الشركات المطورة
@app.route('/companies')
@login_required
def companies():
    companies = DeveloperCompany.query.all()
    return render_template('companies/index.html', companies=companies)

@app.route('/companies/add', methods=['GET', 'POST'])
@login_required
def add_company():
    if request.method == 'POST':
        logo = None
        if 'logo' in request.files:
            file = request.files['logo']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                logo = filename

        company = DeveloperCompany(
            name=request.form['name'],
            license_number=request.form['license_number'],
            description=request.form['description'],
            logo=logo
        )
        db.session.add(company)
        db.session.commit()
        flash('تم إضافة الشركة بنجاح', 'success')
        return redirect(url_for('companies'))

    return render_template('companies/add.html')

@app.route('/companies/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_company(id):
    company = DeveloperCompany.query.get_or_404(id)
    if request.method == 'POST':
        company.name = request.form['name']
        company.license_number = request.form['license_number']
        company.description = request.form['description']

        if 'logo' in request.files:
            file = request.files['logo']
            if file and allowed_file(file.filename):
                # حذف الشعار القديم إذا وجد
                if company.logo:
                    try:
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], company.logo))
                    except:
                        pass
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                company.logo = filename

        db.session.commit()
        flash('تم تحديث الشركة بنجاح', 'success')
        return redirect(url_for('companies'))

    return render_template('companies/edit.html', company=company)

@app.route('/companies/<int:id>/delete', methods=['POST'])
@login_required
def delete_company(id):
    company = DeveloperCompany.query.get_or_404(id)
    if company.logo:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], company.logo))
        except:
            pass
    db.session.delete(company)
    db.session.commit()
    flash('تم حذف الشركة بنجاح', 'success')
    return redirect(url_for('companies'))

# تكوين مجلد مؤقت لتخزين ملفات Excel
TEMP_FOLDER = tempfile.gettempdir()

@app.route('/import_customers', methods=['GET', 'POST'])
@login_required
def import_customers():
    if request.method == 'POST':
        if 'excel_file' not in request.files:
            flash('لم يتم اختيار ملف', 'danger')
            return redirect(request.url)
        
        file = request.files['excel_file']
        if file.filename == '':
            flash('لم يتم اختيار ملف', 'danger')
            return redirect(request.url)
        
        if not file.filename.endswith(('.xlsx', '.xls')):
            flash('يجب أن يكون الملف بصيغة Excel', 'danger')
            return redirect(request.url)
        
        # حفظ الملف مؤقتاً
        temp_path = os.path.join(TEMP_FOLDER, secure_filename(file.filename))
        file.save(temp_path)
        
        try:
            # قراءة الملف وأخذ عينة من البيانات
            df = pd.read_excel(temp_path)
            return redirect(url_for('map_columns', file_path=temp_path))
        except Exception as e:
            os.remove(temp_path)
            flash('حدث خطأ في قراءة الملف', 'danger')
            return redirect(request.url)
    
    return render_template('import_customers.html')

@app.route('/map_columns', methods=['GET', 'POST'])
@login_required
def map_columns():
    file_path = request.args.get('file_path', '')
    if not file_path or not os.path.exists(file_path):
        flash('الملف غير موجود', 'danger')
        return redirect(url_for('import_customers'))
    
    try:
        df = pd.read_excel(file_path)
        
        if request.method == 'POST':
            mapping = {
                'name': request.form.get('name_column'),
                'email': request.form.get('email_column'),
                'phone': request.form.get('phone_column'),
                'facebook_id': request.form.get('facebook_column'),
                'status': request.form.get('status_column'),
                'notes': request.form.get('notes_column')
            }
            
            # التحقق من وجود عمود الاسم
            if not mapping['name']:
                flash('يجب اختيار عمود الاسم', 'danger')
                return redirect(url_for('map_columns', file_path=file_path))
            
            # إضافة العملاء
            success_count = 0
            error_count = 0
            error_details = []
            
            for index, row in df.iterrows():
                try:
                    # التحقق من وجود قيمة في عمود الاسم
                    name_value = str(row[mapping['name']]).strip()
                    if not name_value or pd.isna(name_value):
                        error_details.append(f'سطر {index + 2}: اسم العميل فارغ')
                        error_count += 1
                        continue
                    
                    # معالجة البريد الإلكتروني
                    email_value = None
                    if mapping['email'] and pd.notna(row[mapping['email']]):
                        email_value = str(row[mapping['email']]).strip()
                    
                    # معالجة رقم الهاتف
                    phone_value = None
                    if mapping['phone'] and pd.notna(row[mapping['phone']]):
                        phone_value = str(row[mapping['phone']]).strip()
                    
                    # معالجة معرف الفيس بوك
                    facebook_value = None
                    if mapping['facebook_id'] and pd.notna(row[mapping['facebook_id']]):
                        facebook_value = str(row[mapping['facebook_id']]).strip()
                    
                    # معالجة الحالة
                    status_value = 'new_client'
                    if mapping['status'] and pd.notna(row[mapping['status']]):
                        status_value = str(row[mapping['status']]).strip()
                    
                    # معالجة الملاحظات
                    notes_value = None
                    if mapping['notes'] and pd.notna(row[mapping['notes']]):
                        notes_value = str(row[mapping['notes']]).strip()
                    
                    # إنشاء العميل
                    customer = Customer(
                        name=name_value,
                        email=email_value,
                        phone=phone_value,
                        facebook_id=facebook_value,
                        status=status_value,
                        notes=notes_value
                    )
                    db.session.add(customer)
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    error_details.append(f'سطر {index + 2}: {str(e)}')
                    continue
            
            try:
                db.session.commit()
                os.remove(file_path)
                
                # عرض تفاصيل النجاح والأخطاء
                success_message = f'تم استيراد {success_count} عميل بنجاح.'
                if error_count > 0:
                    error_message = f'فشل استيراد {error_count} عميل.'
                    if len(error_details) > 0:
                        error_message += '<br>التفاصيل:<br>' + '<br>'.join(error_details[:10])
                        if len(error_details) > 10:
                            error_message += f'<br>... و {len(error_details) - 10} أخطاء أخرى'
                    flash(error_message, 'warning')
                
                flash(success_message, 'success')
                return redirect(url_for('customers'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ أثناء حفظ البيانات: {str(e)}', 'danger')
                return redirect(url_for('map_columns', file_path=file_path))
        
        # عرض البيانات للتحديد
        columns = df.columns.tolist()
        preview_data = df.head(5).values.tolist()
        
        return render_template('map_columns.html', 
                             columns=columns, 
                             preview_data=preview_data,
                             file_path=file_path)
                             
    except Exception as e:
        flash(f'حدث خطأ في قراءة الملف: {str(e)}', 'danger')
        return redirect(url_for('import_customers'))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

def init_db():
    # حذف قاعدة البيانات القديمة إذا كانت موجودة
    if os.path.exists('crm.db'):
        os.remove('crm.db')
    # إنشاء قاعدة البيانات الجديدة
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    init_db()  # تهيئة قاعدة البيانات
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
