from flask import Flask, render_template, redirect, url_for, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from models import db, User, Section, Campaign, Influencer, Ad, Transaction, Rating, Bookmark, Flag
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Necessary for session management

app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
 
# Ensure the UPLOAD_FOLDER exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
# Configuration for the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return redirect(url_for('login'))



    
@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.password == password and user.role.lower() == role.lower():
            
            flagged = Flag.query.filter_by(item_type=role, item_id=user.id).first()
            if flagged:
                return render_template('flagged.html')
            
                       
            login_user(user)
            session['role'] = role
            session['username'] = username
            
            print(f"Logged in user: {username}, role: {role}")
            
            # Check if the user is an influencer and has a profile
            if role.lower() == 'influencer':
                influencer = Influencer.query.filter_by(user_id=current_user.id).first()
                print(f"Influencer found: {influencer}")
                
                if influencer:
                    # Fetch campaigns associated with the influencer
                    return redirect(url_for('influencer_dashboard', influencer_id=influencer.id))
                
                else:
                    # No influencer profile found
                    return redirect(url_for('create_influencer'))
            
            # Redirect to different dashboards based on role
            elif role.lower() == 'sponsor':
                return redirect(url_for('sponsor_dashboard', name=username))
            elif role.lower() == 'admin':
                return redirect(url_for('admin_dashboard', name=username))
        
        # If credentials are incorrect, show an error message
        return render_template('wrongpassword.html', message="Wrong password or role")
    
    # If method is GET, render the login form
    return render_template('login.html')




@app.route('/influencer_dashboard/<int:influencer_id>', methods=["GET", "POST"])
@login_required
def influencer_dashboard(influencer_id):

    if current_user.is_authenticated and current_user.role.lower() == 'influencer':
        # Retrieve the specific influencer associated with the current user
        influencer = Influencer.query.filter_by(user_id=current_user.id).first()
        
        if influencer:
            # Retrieve campaigns associated with the influencer
            campaigns = Campaign.query.filter(Campaign.associated_influencers.any(id=influencer.id)).all()
            ad_requests = Ad.query.filter_by(influencer_id=influencer.id).all()
            
            try:
                reach = int(influencer.reach)
            except ValueError:
                reach = 0  # Default value if conversion fails

            if reach >= 500000:
                rating = 5
            elif reach >= 100000:
                rating = 4
            elif reach >= 50000:
                rating = 3
            elif reach >= 10000:
                rating = 2
            elif reach >= 1000:
                rating = 1
            else:
                rating = 0
            total_earnings = sum(ad.payment_amount for ad in ad_requests if ad.status == 'Completed')
               
            return render_template(
                'influencer_dashboard.html', 
                influencer=influencer, 
                influencer_id=influencer.id,
                campaigns=campaigns,
                ad_requests=ad_requests,
                rating=rating,
                total_earnings=total_earnings
            )
        else:
            # Handle case where influencer profile is not found
            return redirect(url_for('create_influencer'))
    else:
        # Handle case where user is not authenticated or not an influencer
        return redirect(url_for('login'))


@app.route('/create_influencer', methods=["GET", "POST"])
@login_required
def create_influencer():
    influencer = Influencer.query.filter_by(user_id=current_user.id).first()
    
    if request.method == "POST":
        name = request.form.get("name")
        platform = request.form.get("platform")
        niche = request.form.get("niche")
        reach = request.form.get("reach")
        profile_picture = request.files.get("profile_picture")

        filename = None
        if profile_picture and profile_picture.filename != '':
            if allowed_file(profile_picture.filename):
                filename = secure_filename(profile_picture.filename)
                profile_picture.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            else:
                return redirect(request.url)

        if influencer:
            influencer.name = name
            influencer.platform = platform
            influencer.niche = niche
            influencer.reach = reach
            if filename:
                influencer.profile_picture = filename
        else:
            influencer = Influencer(
                user_id=current_user.id,
                name=name,
                platform=platform,
                niche=niche,
                reach=reach,
                profile_picture=filename
            )
            db.session.add(influencer)
        
        db.session.commit()
        
        if influencer is None:
            return redirect(request.url)
        
        public_campaigns = Campaign.query.filter_by(visibility='Public').all()
        for campaign in public_campaigns:
            # Fetch existing ads for the campaign
            existing_ads = Ad.query.filter_by(campaign_id=campaign.id).all()
            for existing_ad in existing_ads:
                # Ensure existing_ad is not None
                if existing_ad:
                    # Check if an ad already exists for this influencer and campaign to avoid duplicates
                    ad_duplicate_check = Ad.query.filter_by(campaign_id=campaign.id, influencer_id=influencer.id).first()
                    if not ad_duplicate_check:
                        new_ad = Ad(
                            campaign_id=campaign.id,
                            influencer_id=influencer.id,
                            messages=existing_ad.messages,
                            requirements=existing_ad.requirements,
                            payment_amount=existing_ad.payment_amount,
                            status='Pending'  # Default status
                        )
                        db.session.add(new_ad)
        
        db.session.commit()
        return redirect(url_for('influencer_dashboard', influencer_id=current_user.id))
    
    return render_template('create_influencer.html')

@app.route('/delete_influencer_account', methods=['POST'])
@login_required
def delete_influencer_account():
    influencer = Influencer.query.filter_by(user_id=current_user.id).first()
    
    if influencer:
        # Delete all ads related to this influencer
        Ad.query.filter_by(influencer_id=influencer.id).delete()
        
        # Delete all transactions related to this influencer
        Transaction.query.filter_by(influencer_id=influencer.id).delete()
        
        # Delete the influencer
        db.session.delete(influencer)
    
    # Delete the user
    user = User.query.get(current_user.id)
    db.session.delete(user)
    
    db.session.commit()
    
    # Log out the user
    logout_user()
    
    return redirect(url_for('login'))


@app.route('/delete_sponsor/<int:sponsor_id>', methods=['POST'])
@login_required
def delete_sponsor(sponsor_id):
    # Fetch the sponsor by the current logged-in user
    sponsor = User.query.get_or_404(sponsor_id)

    if sponsor is None:
        # If no sponsor is found, return an error or redirect
        return "Sponsor not found or not a sponsor", 404

    # Fetch associated campaigns using the sponsor's ID
    campaigns = Campaign.query.filter_by(user_id=sponsor.id).all()
    
    # Iterate through campaigns and their ads to delete associated transactions
    for campaign in campaigns:
        ads = Ad.query.filter_by(campaign_id=campaign.id).all()
        for ad in ads:
            # Fetch and delete associated transactions
            transactions = Transaction.query.filter_by(ad_request_id=ad.id).all()
            for transaction in transactions:
                db.session.delete(transaction)
            
            # Delete the ad
            db.session.delete(ad)
        
        # Delete the campaign
        db.session.delete(campaign)
    
    # Finally, delete the sponsor
    db.session.delete(sponsor)
    
    # Commit all changes
    try:
        db.session.commit()
        return redirect(url_for('admin_profile'))
    except Exception as e:
        db.session.rollback()
        return "An error occurred while deleting the sponsor", 500



@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('role', None)
    session.pop('username', None)
    return render_template('logout.html')

@app.route('/userdashboard')
@login_required
def userdashboard():
    return render_template('userdashboard.html')


@app.route('/influencer_profile', methods=["GET", "POST"])
def influencer_profile():
    if current_user.is_authenticated and current_user.role == 'influencer':
        influencer = Influencer.query.filter_by(user_id=current_user.id).first()
        if influencer:
            return render_template('influencer_profile.html', influencer=influencer)
        else:
            
            return redirect(url_for('create_influencer'))
    else:
       
        return redirect(url_for('login'))

@app.route('/influencer_find')
@login_required
def influencer_find():
    return render_template('influencer_find.html')



@app.route('/createnew_section')
@login_required
def createnew_section():
    return render_template('createnew_section.html')

'''
@app.route('/sponsor_dashboard', methods=["GET", "POST"])
@login_required
def sponsor_dashboard():
    # Fetch campaigns and influencers
    campaigns = Campaign.query.all()
    influencers = Influencer.query.all()
    sponsor_id = current_user.id
    print(f"Current user ID: {current_user.id}")  # Debug print for current user ID
    public_campaigns = Campaign.query.filter_by(user_id=sponsor_id, visibility='Public').all()
    private_campaigns = Campaign.query.filter_by(user_id=sponsor_id, visibility='Private').all()
    
    print(f"Sponsor ID: {sponsor_id}")  # Debug print for sponsor ID
    print("Public Campaigns:", public_campaigns)  # Debug print for public campaigns
    print("Private Campaigns:", private_campaigns)
    
    # Just for demonstration, picking the first campaign and influencer
    campaign = campaigns[0] if campaigns else None
    influencer = influencers[0] if influencers else None
    return render_template('sponsor_dashboard.html', public_campaigns=public_campaigns, private_campaigns=private_campaigns, campaign=campaign, influencer=influencer)
'''

@app.route('/sponsor_dashboard', methods=["GET", "POST"])
@login_required
def sponsor_dashboard():

    sponsor_id = current_user.id

    public_campaigns = Campaign.query.filter_by(user_id=sponsor_id, visibility='Public').all()
    private_campaigns = Campaign.query.filter_by(user_id=sponsor_id, visibility='Private').all()

    flagged_campaigns = {flag.item_id for flag in Flag.query.filter_by(item_type='Campaign').all()}
    campaigns =  Campaign.query.filter_by(user_id=current_user.id).all()
    visible_campaigns = [campaign for campaign in campaigns if campaign.id not in flagged_campaigns]
    
    def calculate_progress(campaign):
        total_ads = len(campaign.ads)
        if total_ads == 0:
            return 0
        completed_ads = sum(1 for ad in campaign.ads if ad.status == 'Completed')
        return int((completed_ads / total_ads) * 100)

    public_campaigns_progress = [(campaign, calculate_progress(campaign)) for campaign in public_campaigns]
    private_campaigns_progress = [(campaign, calculate_progress(campaign)) for campaign in private_campaigns]

    
    print(f"Sponsor ID: {sponsor_id}")  # Debug print for sponsor ID
    print("Public Campaigns:", public_campaigns)  # Debug print for public campaigns
    print("Private Campaigns:", private_campaigns)  # Debug print for private campaigns

    return render_template('sponsor_dashboard.html', public_campaigns=public_campaigns_progress, private_campaigns=private_campaigns_progress, campaign=visible_campaigns)


@app.route('/sponsor_find')
@login_required
def sponsor_find():
    return render_template('sponsor_find.html')

@app.route('/sponsor_profile')
@login_required
def sponsor_profile():
    return render_template('sponsor_profile.html')

@app.route('/success')
@login_required
def success():
    return render_template('success.html')

@app.route('/influencer_reg', methods=["GET", "POST"])
def influencer_reg():
    if request.method == "POST":
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        new_user = User(name=name, username=username, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
        return render_template('success.html')
    return render_template('influencer_reg.html')

@app.route('/sponsor_reg', methods=["GET", "POST"])
def sponsor_reg():
    if request.method == "POST":
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        new_user = User(name=name, username=username, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
        return render_template('success.html')
    return render_template('sponsor_reg.html')

@app.route('/admin_reg', methods=["GET", "POST"])
def admin_reg():
    if request.method == "POST":
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        new_user = User(name=name, username=username, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('success'))
    return render_template('admin_reg.html')



@app.route('/influencer/update/<int:influencer_id>', methods=["GET", "POST"])
def update_influencer(influencer_id):
    influencer = Influencer.query.get(influencer_id)
    if request.method == "POST":
        influencer.name = request.form['name']
        influencer.platform = request.form['platform']
        influencer.niche = request.form['niche']
        influencer.reach = request.form['reach']
        db.session.commit()
        return redirect(url_for('show_influencers'))
    return render_template('update_influencer.html', influencer=influencer)

@app.route('/influencer/delete/<int:influencer_id>', methods=["POST"])
def delete_influencer(influencer_id):
    influencer = Influencer.query.get(influencer_id)
    db.session.delete(influencer)
    db.session.commit()
    return redirect(url_for('create_influencer'))

@app.route('/show_influencers', methods=["GET"])
def show_influencers():
    influencers = Influencer.query.all()
    return render_template('create_influencer.html', influencers=influencers)

#sposnors can view influencers
@app.route('/view_influencers_to_sponsor')
@login_required
def view_influencers_to_sponsor():
    influencers = Influencer.query.all()
    return render_template('view_influencers_to_sponsor.html', influencers=influencers)

@app.route('/create_campaign', methods=["GET", "POST"])
def create_campaign():
    return render_template('create_campaign.html')

@app.route('/campaign', methods=["GET", "POST"])
def campaign():
    if request.method == "POST":
        campaign_name = request.form['name']
        description = request.form['description']
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
        budget = int(request.form['budget'])
        visibility = request.form['visibility']
        goals = request.form['goals']
        niche = request.form['niche']
        if niche == 'Other':
            niche = request.form['other_niche']

        new_campaign = Campaign(name=campaign_name, description=description, start_date=start_date,
                                end_date=end_date, budget=budget, visibility=visibility, goals=goals, niche=niche, user_id=current_user.id )
        
        db.session.add(new_campaign)
        db.session.commit()

    campaigns = Campaign.query.filter_by(user_id=current_user.id).all()
    return render_template('create_campaign.html',campaigns=campaigns)

@app.route('/show_campaign', methods=["GET", "POST"])
def show_campaign():
    if request.method == "POST":
        pass  # Handle any POST requests if needed
    flagged_campaigns = {flag.item_id for flag in Flag.query.filter_by(item_type='Campaign').all()}
    campaigns =  Campaign.query.filter_by(user_id=current_user.id).all()
    visible_campaigns = [campaign for campaign in campaigns if campaign.id not in flagged_campaigns]
    influencers = Influencer.query.all()
    return render_template('create_campaign.html', campaigns=visible_campaigns, influencers=influencers)

@app.route('/campaign/update/<int:campaign_id>', methods=["GET", "POST"])
def update_campaign(campaign_id):
    campaign = Campaign.query.get(campaign_id)
    if request.method == "POST":
        campaign.name = request.form['name']
        campaign.description = request.form['description']
        campaign.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        campaign.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
        campaign.budget = int(request.form['budget'])
        campaign.visibility = request.form['visibility']
        campaign.goals = request.form['goals']
        campaign.niche = request.form.get('niche', 'Other')
        db.session.commit()
        return redirect(url_for('show_campaign'))
    return render_template('update_campaign.html', campaign=campaign)

@app.route('/campaign/delete/<int:campaign_id>', methods=["POST"])
def delete_campaign(campaign_id):
    campaign = Campaign.query.get(campaign_id)
    if campaign:
        # Delete associated ads first
        ads = Ad.query.filter_by(campaign_id=campaign_id).all()
        for ad in ads:
            db.session.delete(ad)
        
        # Then delete the campaign
        db.session.delete(campaign)
        db.session.commit()
    
    return redirect(url_for('campaign'))



#for creating ads of the private campaigns (for a specific influencer)
@app.route('/ad_requirements/<int:influencer_id>/<int:campaign_id>', methods=['GET', 'POST'])
def ad_requirements(influencer_id, campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    influencer = Influencer.query.get_or_404(influencer_id)
    if request.method == 'POST':
        requirements = request.form['requirements']
        messages = request.form['messages']
        payment_amount = request.form['payment_amount']

        new_ad_request = Ad(
            influencer_id=influencer_id,
            campaign_id=campaign_id,
            requirements=requirements,
            messages=messages,
            payment_amount=payment_amount,
            status='Pending'
        )
        db.session.add(new_ad_request)
        db.session.commit()

        return redirect(url_for('campaign_influencer', campaign_id=campaign_id, influencer_id=influencer_id))

    return render_template('ad_requirements.html', campaign_id=campaign_id, influencer_id=influencer_id)


@app.route('/influencer_priv_adrequests/<int:influencer_id>', methods=['GET','POST'])
@login_required
def influencer_priv_adrequests(influencer_id):
    influencer = Influencer.query.get_or_404(influencer_id)
    print(f"Influencer fetched: {influencer}")
    # Fetch all flagged campaign IDs
    flagged_campaigns = {flag.item_id for flag in Flag.query.filter_by(item_type='Campaign').all()}
    # Fetch all ad requests for the influencer
    ad_requests = Ad.query.filter_by(influencer_id=influencer_id).all()
    print(f"Ad requests: {ad_requests}")
    # Fetch campaign details for each ad request
    ad_requests = [ad for ad in ad_requests if ad.campaign_id not in flagged_campaigns]
    ad_requests_with_campaigns = []
    for ad in ad_requests:
        campaign = Campaign.query.get(ad.campaign_id)
        ad_requests_with_campaigns.append((ad, campaign))
    campaign_id = ad_requests[0].campaign_id if ad_requests else None
    return render_template('influencer_priv_adrequests.html', ad_requests_with_campaigns=ad_requests_with_campaigns, influencer=influencer,campaign_id=campaign_id, influencer_id=influencer.id)



@app.route('/add_ads/<int:campaign_id>', methods=['GET', 'POST'])
def add_ads(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    influencers = Influencer.query.all()
    
    if campaign.visibility == 'Private' and influencers:
        # Redirect to the first influencer in the list
        return redirect(url_for('campaign_influencer', campaign_id=campaign.id, influencer_id=influencers[0].id))

    if request.method == 'POST':
        messages = request.form['messages']
        requirements = request.form['requirements']
        payment_amount = request.form['payment_amount']
        status = request.form['status']

        for influencer in influencers:
            new_ad = Ad(campaign_id=campaign.id, influencer_id=influencer.id, messages=messages,
                        requirements=requirements, payment_amount=payment_amount, status=status)
            db.session.add(new_ad)
        db.session.commit()

        return redirect(url_for('show_campaign'))

    return render_template('add_ads.html', campaign=campaign, influencers=influencers)


@app.route('/view_ads/<int:campaign_id>', methods=['GET'])
def view_ads(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    ads = Ad.query.filter_by(campaign_id=campaign_id).all()
    
    for ad in ads:
        influencer = Influencer.query.get(ad.influencer_id)
        ad.influencer_name = influencer.name if influencer else 'Unknown'
    return render_template('view_ads.html', campaign=campaign, ads=ads)


@app.route('/update_ad/<int:ad_id>', methods=['GET', 'POST'])
def update_ad(ad_id):
    ad = Ad.query.get_or_404(ad_id)

    if request.method == 'POST':
        ad.messages = request.form['messages']
        ad.requirements = request.form['requirements']
        ad.payment_amount = request.form['payment_amount']
        ad.status = request.form['status']

        try:
            db.session.commit()
            return redirect(url_for('view_ads', campaign_id=ad.campaign_id))
        except:
            return 'Error updating ad'

    return render_template('update_ad.html', ad=ad)

@app.route('/delete_ad/<int:ad_id>', methods=['POST'])
def delete_ad(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    campaign_id = ad.campaign_id  # Ensure campaign_id is fetched before deletion

    try:
        db.session.delete(ad)
        db.session.commit()
        return redirect(url_for('view_ads', campaign_id=campaign_id))
    except Exception as e:
        db.session.rollback()
        print(e)  # Print the actual exception for debugging
        return redirect(url_for('view_ads', campaign_id=campaign_id))


@app.route('/campaign_influencer/<int:campaign_id>/<int:influencer_id>', methods=['GET', 'POST'])
def campaign_influencer(campaign_id, influencer_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    influencers = Influencer.query.all()
    
    #for search functionality
    name = request.args.get('name')
    niche = request.args.get('niche')
    reach = request.args.get('reach')
     # Base query
    query = Influencer.query

    # Apply filters based on search criteria
    if name:
        query = query.filter(Influencer.name.ilike(f"%{name}%"))
    if niche:
        query = query.filter(Influencer.niche.ilike(f"%{niche}%"))
    if reach:
        query = query.filter(Influencer.reach == reach)

    influencers = query.all()
    
    return render_template('campaign_influencer.html', campaign_id=campaign_id, influencer_id=influencer_id, campaign=campaign, influencers=influencers)

@app.route('/show_influencers1', methods=["GET"])
def show_influencers1():
    influencers = Influencer.query.all()
    return render_template('campaign_influencer.html', campaign=campaign, influencers=influencers)

@app.route('/search_influencers', methods=['GET'])
def search_influencers():
    name = request.args.get('name')
    category = request.args.get('category')
    niche = request.args.get('niche')
    reach = request.args.get('reach')
    
    # Start with a base query
    query = Influencer.query
    
    # Add filters to the query based on search criteria
    if name:
        query = query.filter(Influencer.name.ilike(f"%{name}%"))
    if category:
        query = query.filter(Influencer.category.ilike(f"%{category}%"))
    if niche:
        query = query.filter(Influencer.niche.ilike(f"%{niche}%"))
    if reach:
        query = query.filter(Influencer.reach.ilike(f"%{reach}%"))
    
    # Execute the query to get the filtered influencers
    filtered_influencers = query.all()
    
    return render_template('campaign_influencer.html', influencers=filtered_influencers)



@app.route('/influencer_campaign', methods=["GET", "POST"])
@login_required
def influencer_campaign():
    flagged_campaigns = {flag.item_id for flag in Flag.query.filter_by(item_type='Campaign').all()}
    campaigns = Campaign.query.filter_by(visibility='Public').all()
    campaigns = [campaign for campaign in campaigns if campaign.id not in flagged_campaigns]
    influencers = Influencer.query.all()
    current_user_id = current_user.id  # Fetch the ID of the currently logged-in user
    print(f"Current user ID: {current_user_id}")  # Debug print to see the current user ID
    return render_template('influencer_campaign.html', campaigns=campaigns, influencers=influencers, current_user_id=current_user_id)


@app.route('/search_campaigns', methods=["GET","POST"])
def search_campaigns():
    name = request.args.get('name', '')
    niche = request.args.get('niche', '')  # Changed from category to niche
    budget_min = request.args.get('budget_min', '')
    budget_max = request.args.get('budget_max', '')
    
    query = Campaign.query.filter_by(visibility='Public')    
    
    if name:
        query = query.filter(Campaign.name.ilike(f'%{name}%'))    
    if niche:
        query = query.filter(Campaign.niche.ilike(f'%{niche}%'))    
    if budget_min:
        try:
            budget_min = float(budget_min)
            query = query.filter(Campaign.budget >= budget_min)
        except ValueError:
            pass  # Handle invalid input for min budget
    if budget_max:
        try:
            budget_max = float(budget_max)
            query = query.filter(Campaign.budget <= budget_max)
        except ValueError:
            pass  # Handle invalid input for max budget
    
    campaigns = query.all()
    return render_template('influencer_campaign.html', campaigns=campaigns)



@app.route('/accept_ad/<int:ad_id>', methods=['GET', 'POST'])
@login_required
def accept_ad(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    ad.status = 'Accepted'
    db.session.commit()
    #return redirect(url_for('active_campaigns'))
    return redirect(url_for('influencer_priv_adrequests', influencer_id=ad.influencer_id))


@app.route('/reject_ad/<int:ad_id>', methods=['GET', 'POST'])
@login_required
def reject_ad(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    ad.status = 'Rejected'
    db.session.commit()
    #return redirect(url_for('influencer_ads', campaign_id=ad.campaign_id))
    return redirect(url_for('influencer_priv_adrequests', influencer_id=ad.influencer_id))


@app.route('/negotiate_ad/<int:ad_id>', methods=['GET', 'POST'])
@login_required
def negotiate_ad(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    new_status = request.form.get('new_status', 'Negotiating')
    ad.status = new_status
    db.session.commit()
    return redirect(url_for('influencer_priv_adrequests', influencer_id=ad.influencer_id))

@app.route('/manage_negotiated_ads', methods=['GET'])
@login_required
def manage_negotiated_ads():
    # Filter ads where status is not 'Accepted', 'Rejected', or 'Completed'
    excluded_statuses = ['Accepted', 'Rejected', 'Completed', 'Pending','Transaction Done']
    negotiated_ads = Ad.query.filter(~Ad.status.in_(excluded_statuses)).all()   
    return render_template('manage_negotiated_ads.html', ads=negotiated_ads)



@app.route('/influencer_ads/<int:campaign_id>', methods=['GET','POST'])
@login_required
def influencer_ads(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    
    # Fetch the influencer corresponding to the current user
    influencer = Influencer.query.filter_by(user_id=current_user.id).first()
    current_user_id = current_user.id
    # Debug prints
    print(f"Current user ID: {current_user.id}")
    print(f"Fetched influencer: {influencer}")
    
    # Ensure the influencer is found
    if influencer is None:
        # Handle the case where the user is not an influencer

        pass
    
    print(f"Influencer ID: {influencer.id}")

    ads = Ad.query.filter_by(campaign_id=campaign_id, influencer_id=influencer.id, status='Pending').all()
    return render_template('influencer_ads.html', campaign=campaign, ads=ads, influencer=influencer, current_user_id=current_user_id)




@app.route('/accept_ad11/<int:ad_id>', methods=['GET', 'POST'])
@login_required
def accept_ad11(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    ad.status = 'Accepted'
    db.session.commit()
    #return redirect(url_for('active_campaigns'))
    return redirect(url_for('influencer_ads', campaign_id=ad.campaign_id))

@app.route('/reject_ad11/<int:ad_id>', methods=['GET', 'POST'])
@login_required
def reject_ad11(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    ad.status = 'Rejected'
    db.session.commit()
    #return redirect(url_for('influencer_ads', campaign_id=ad.campaign_id))
    return redirect(url_for('influencer_ads', campaign_id=ad.campaign_id))

#as the influencer sees the ads of public campaigns and requests the sponsor
@app.route('/request_ad11/<int:ad_id>', methods=['GET', 'POST'])
@login_required
def request_ad11(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    ad.status = 'Requested'
    db.session.commit()
    #return redirect(url_for('influencer_ads', campaign_id=ad.campaign_id))
    return redirect(url_for('influencer_ads', campaign_id=ad.campaign_id))


@app.route('/negotiate_ad11/<int:ad_id>', methods=['GET', 'POST'])
@login_required
def negotiate_ad11(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    new_status = request.form.get('new_status', 'Negotiating')
    ad.status = new_status
    db.session.commit()
    return redirect(url_for('influencer_ads', campaign_id=ad.campaign_id))


#This will let sponsor manage the requested and negotiated ads by the influencer (for the public campaigns)
@app.route('/manage_negotiated_ads11', methods=['GET'])
@login_required
def manage_negotiated_ads11():
    # Assuming the sponsor is the current user
    excluded_statuses = ['Accepted', 'Rejected', 'Completed', 'Pending','Transaction Done']
    negotiated_ads = Ad.query.filter(~Ad.status.in_(excluded_statuses)).all()   
    return render_template('manage_negotiated_ads.html', ads=negotiated_ads)


@app.route('/accept_negotiated_ad/<int:ad_id>', methods=['GET', 'POST'])
@login_required
def accept_negotiated_ad(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    ad.status = 'Accepted'
    db.session.commit()
    #return redirect(url_for('active_campaigns'))
    return redirect(url_for('manage_negotiated_ads11'))


@app.route('/reject_negotiated_ad/<int:ad_id>', methods=['GET', 'POST'])
@login_required
def reject_negotiated_ad(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    ad.status = 'Rejected'
    db.session.commit()
    #return redirect(url_for('influencer_ads', campaign_id=ad.campaign_id))
    return redirect(url_for('manage_negotiated_ads11'))


@app.route('/update_negotiated_ad/<int:ad_id>', methods=['GET', 'POST'])
def update_negotiated_ad(ad_id):
    ad = Ad.query.get_or_404(ad_id)

    if request.method == 'POST':
        ad.messages = request.form['messages']
        ad.requirements = request.form['requirements']
        ad.payment_amount = request.form['payment_amount']
        ad.status = request.form.get('status', 'Accepted')

        try:
            db.session.commit()
            return redirect(url_for('manage_negotiated_ads11'))
        except:
            return 'Error updating ad'

    return render_template('update_negotiated_ad.html', ad=ad)


@app.route('/active_campaigns/<int:influencer_id>', methods=['GET', 'POST'])
@login_required
def active_campaigns(influencer_id):
    influencer = Influencer.query.get_or_404(influencer_id)
    ads = Ad.query.filter_by(influencer_id=influencer.id, status='Accepted').all()
    # Debug output
    print(f"Current user ID: {current_user.id}")
    print(f"Influencer ID: {influencer.id}")
    print(f"Ads fetched for active campaigns: {ads}")
    
    return render_template('active_campaigns.html', influencer=influencer, influencer_id=influencer.id, ads=ads)






@app.route('/search_privatecampaigns', methods=["GET", "POST"])
def search_privatecampaigns():
    name = request.args.get('name', '')

    query = Campaign.query.filter_by(visibility='Private')
    if name:
        query = query.filter(Campaign.name.ilike(f'%{name}%'))
    
    campaigns = query.all()
    
    return render_template('influencer_priv_adrequests.html', campaigns=campaigns)


@app.route('/mark_as_completed/<int:ad_id>', methods=["GET", "POST"])
@login_required
def mark_as_completed(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    if ad.status != 'Completed':
        ad.status = 'Completed'
        db.session.commit()
    return redirect(url_for('active_campaigns', influencer_id=ad.influencer_id))  # Redirect back to the active campaigns page

@app.route('/completed_campaigns',  methods=["GET", "POST"])
@login_required
def completed_campaigns():
    ads = Ad.query.filter_by(status='Completed').all()
    ads_with_transactions = []
    for ad in ads:
        transaction = Transaction.query.filter_by(ad_request_id=ad.id).first()
        ads_with_transactions.append({
            'ad': ad,
            'transaction': transaction
        })
    
    return render_template('completed_campaigns.html', ads=ads, ads_with_transactions=ads_with_transactions)


def get_transaction_by_ad_id(ad_id):
    return Transaction.query.filter_by(ad_request_id=ad_id).first()

@app.route('/transaction/<int:ad_id>', methods=['GET', 'POST'])
@login_required
def transaction(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    transaction = Transaction.query.filter_by(ad_request_id=ad_id).first()
    
    if transaction is None:
        # Create a new transaction if it doesn't exist
        transaction = Transaction(
            influencer_id=ad.influencer_id,
            user_id=current_user.id,
            amount=ad.payment_amount,
            status='Transaction done',
            ad_request_id=ad_id,
            request_type='Private'  # Adjust as necessary
        )
        db.session.add(transaction)
        db.session.commit()
    
    if request.method == 'POST':
        # Ensure transaction is not None before modifying
        if transaction:
            transaction.amount = request.form.get('amount', transaction.amount)
            transaction.status = 'Transaction Done'  # Update status to 'Transaction Done'
            db.session.commit()
            return redirect(url_for('completed_campaigns'))
        else:
            # Handle the case where transaction is None (should not occur in normal flow)
            return "Transaction not found", 404

    return render_template('transaction.html', transaction=transaction, ad=ad)



@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    # Fetching counts for influencers and sponsors
    influencers_count = Influencer.query.count()
    sponsors_count = User.query.filter_by(role='Sponsor').count()

    # Fetching ad statuses
    ad_status_counts = {
        'Accepted': Ad.query.filter_by(status='Accepted').count(),
        'Rejected': Ad.query.filter_by(status='Rejected').count(),
        'Completed': Ad.query.filter_by(status='Completed').count(),
        'Pending': Ad.query.filter_by(status='Pending').count(),
        'Transaction Done': Ad.query.filter_by(status='Transaction Done').count(),
        'Other': Ad.query.filter_by(status='Other').count()
    }

    private_campaigns_count = Campaign.query.filter_by(visibility='Private').count()
    public_campaigns_count = Campaign.query.filter_by(visibility='Public').count()
    
    # Count completed and incomplete campaigns
    completed_campaigns_count = Campaign.query.filter(
        Campaign.ads.any(Ad.status != 'Completed')
    ).count()
    incomplete_campaigns_count = Campaign.query.filter(
        Campaign.ads.any(Ad.status == 'Completed')
    ).count()


    return render_template('admin_dashboard.html',
                           influencers_count=influencers_count,
                           sponsors_count=sponsors_count,
                           ad_status_counts=ad_status_counts,
                           private_campaigns_count=private_campaigns_count,
                           public_campaigns_count=public_campaigns_count,
                           completed_campaigns_count=completed_campaigns_count,
                           incomplete_campaigns_count=incomplete_campaigns_count)


@app.route('/admin_profile')
@login_required
def admin_profile():
    influencers = Influencer.query.all()
    sponsors = User.query.filter_by(role='Sponsor').all()
    campaigns = Campaign.query.all()
    
    ongoing_campaigns = []
    completed_campaigns = []
    flagged_items = Flag.query.all()

    for campaign in campaigns:
        ads = campaign.ads
        all_completed = all(ad.status == 'Completed' for ad in ads)
        if all_completed:
            completed_campaigns.append(campaign)
        else:
            ongoing_campaigns.append(campaign)
    
    return render_template('admin_profile.html',flagged_items = flagged_items, ongoing_campaigns=ongoing_campaigns, completed_campaigns=completed_campaigns, influencers=influencers, campaigns=campaigns, sponsors=sponsors)

@app.route('/admin_find')
@login_required
def admin_find():
    influencers = User.query.filter_by(role='Influencer').all()
    sponsors = User.query.filter_by(role='Sponsor').all()
    campaigns = Campaign.query.all()
    flags = Flag.query.all()
    
    flagged_item_ids = {f'{flag.item_type}_{flag.item_id}': flag.id for flag in flags}
    
    print("Influencers:", influencers)
    print("Sponsors:", sponsors)
    print("Campaigns:", campaigns)
    print("Flagged Item IDs:", flagged_item_ids)
    
    return render_template('admin_find.html', influencers=influencers, sponsors=sponsors, campaigns=campaigns, flagged_item_ids=flagged_item_ids)


#for admin_find page

@app.route('/view_influencer/<int:influencer_id>')
@login_required
def view_influencer(influencer_id):
    influencer = Influencer.query.get_or_404(influencer_id)
    
    # Fetch active ads
    active_ads = Ad.query.filter_by(influencer_id=influencer.id, status='Accepted').all()
    print(f"Active ads: {active_ads}")

    # Fetch completed ads
    completed_ads = Ad.query.filter_by(influencer_id=influencer.id, status='Completed').all()
    print(f"Completed ads: {completed_ads}")
    
    return render_template('admin_view_influencer.html', influencer=influencer, active_ads=active_ads, completed_ads=completed_ads)


@app.route('/view_sponsor/<int:sponsor_id>')
@login_required
def view_sponsor(sponsor_id):
    sponsor = User.query.get_or_404(sponsor_id)
    public_campaigns = Campaign.query.filter_by(user_id=sponsor.id, visibility='Public').all()
    private_campaigns = Campaign.query.filter_by(user_id=sponsor.id, visibility='Private').all()
    return render_template('admin_view_sponsor.html', sponsor=sponsor, public_campaigns=public_campaigns, private_campaigns=private_campaigns)

@app.route('/view_campaign/<int:campaign_id>')
@login_required
def view_campaign(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    ads = Ad.query.filter_by(campaign_id=campaign.id).all()
    return render_template('admin_view_campaign.html', campaign=campaign, ads=ads)

@app.route('/flag/<item_type>/<int:item_id>', methods=['POST'])
@login_required
def flag_item(item_type, item_id):
    reason = request.form.get('reason')
    if not reason:
        
        return redirect(request.referrer)
    
    new_flag = Flag(item_type=item_type, item_id=item_id, reason=reason)
    db.session.add(new_flag)
    db.session.commit()
    
    return redirect(request.referrer)


@app.route('/remove_flag/<int:flag_id>', methods=['POST'])
@login_required
def remove_flag(flag_id):
    flag = Flag.query.get_or_404(flag_id)
    db.session.delete(flag)
    db.session.commit()
    return redirect(request.referrer)

@app.route('/stats/<int:influencer_id>')
@login_required
def stats(influencer_id):
    if current_user.is_authenticated and current_user.role.lower() == 'influencer':
        influencer = Influencer.query.get_or_404(influencer_id)
        ad_requests = Ad.query.filter_by(influencer_id=influencer_id).all()
        
        completed_requests = [ad for ad in ad_requests if ad.status == 'Completed']
        #transaction_requests = [ad for ad in ad_requests if ad.status == 'Transaction Done']
        
        completed_requests_count = len(completed_requests)
        ad_requests_count = len(ad_requests)
        payment_received = sum(ad.payment_amount for ad in completed_requests)
        
        # Prepare data for charts
        labels = ['Ad Requests Received', 'Completed Ad Requests']
        completed_vs_received = [ad_requests_count, completed_requests_count]

        return render_template('stats.html',
                               influencer=influencer,
                               influencer_id=influencer.id,
                               ad_requests=ad_requests,
                               completed_requests=completed_requests,
                               payment_received=payment_received,
                               completed_vs_received=completed_vs_received)
    else:
        return redirect(url_for('login'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Check if admin user exists, if not, create one
        admin_user = User.query.filter_by(role='admin').first()
        if not admin_user:
            admin_user = User(name='admin', username='admin', password='admin', role='admin')
            db.session.add(admin_user)
            db.session.commit()
    app.run(debug=True)
