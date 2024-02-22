from django.shortcuts import render, redirect, get_object_or_404
from .models import Event, Member, Expense, UserPreferences, Transaction
from django.contrib import messages
from django.db.models import Sum, Count
from django.db.models.functions import ExtractYear, ExtractMonth
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from .forms import EventForm, MemberForm, ExpenseForm, CustomUserCreationForm, ForgotPasswordForm, TransactionForm
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import F, ExpressionWrapper, fields
from django.db.models.functions import ExtractMonth, ExtractDay

import logging
from django.contrib.auth import logout
from django.contrib.auth.forms import AuthenticationForm
from django.utils.html import strip_tags
from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist

from django.urls import reverse_lazy
from django.contrib.auth import views as auth_views
# Create your views here.

def user_login(request):
    dynamic_title = "Login"

    if request.method == 'POST':
        form = AuthenticationForm(request=request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            # Authenticate the user
            user = authenticate(request, username=username, password=password)

            if user is not None:
                if user.is_active:
                    # Log the user in
                    login(request, user)
                    messages.success(request, "You have successfully logged in.")
                    return redirect('home')
                else:
                    messages.error(request, "Your account is not activated.")
            else:
                # Invalid credentials
                messages.error(request, "Invalid username or password. Please try again.")
        else:
            # Form is not valid (likely missing username or password)
            messages.error(request, "Invalid form submission. Please provide both username and password.")
    else:
        form = AuthenticationForm()

    return render(request, 'expenses/login.html', {'form': form, 'dynamic_title': dynamic_title})

@login_required(login_url='login')
def user_profile(request):
    user=request.user
    dynamic_title = f"Profile ({user.username})"
    context = {
        'dynamic_title':dynamic_title
    }
    return render(request, 'expenses/profile.html', context)

@login_required(login_url='login')
def user_settings(request):
    user = request.user
    user_profile, created = UserPreferences.objects.get_or_create(user=user)

    if request.method == 'POST':
        dark_mode = request.POST.get('dark_mode', None)
        if dark_mode is not None:
            user_profile.dark_mode = dark_mode == 'true'
            user_profile.save()
            if dark_mode == 'true':
                messages.success(request, "Switched to Dark Mode")
            else:
                messages.success(request, "Switched to Light Mode")
            return JsonResponse({'status': 'success'})

    dynamic_title = f"Settings ({user.username})"
    context = {
        'dynamic_title': dynamic_title,
        'dark_mode_preference': user_profile.dark_mode,
    }

    return render(request, 'expenses/settings.html', context)

logger = logging.getLogger(__name__)

def user_signup(request):
    dynamic_title = "Signup"
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            logger.debug(f"User created: {user}")
            email = form.cleaned_data.get('email')

            # Log the user in
            # login(request, user)

            # Send email verification link
            current_site = get_current_site(request)
            mail_subject = 'Activate your account'
            message = render_to_string('expenses/account_activation_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            
            # Remove HTML tags from the email message
            plain_text_message = strip_tags(message)

            email = EmailMultiAlternatives(mail_subject, plain_text_message, to=[email])
            email.attach_alternative(message, "text/html")  # Attach the HTML version

            # Send the email
            email.send()

            # Redirect to a success page after successful signup (change 'home' to your desired URL)
            messages.success(request, "Account created successfully.")
            return redirect('home')
        else:
            messages.error(request, 'Something went wrong.')
    else:
        # Use an empty UserCreationForm for initial rendering of the form
        form = CustomUserCreationForm()

    return render(request, 'expenses/signup.html', {'form': form, 'dynamic_title': dynamic_title})

User = get_user_model()

def account_activation(request, uidb64, token):
    dynamic_title = "Account Activation"
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, ValidationError, User.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        # Activate the user account
        user.is_active = True
        user.save()
        return render(request, 'expenses/account_activation_success.html', {'user': user, 'dynamic_title': dynamic_title})
    else:
        dynamic_title = "Activation Failed"
        return render(request, 'expenses/account_activation_failure.html', {'dynamic_title': dynamic_title})

@login_required(login_url='login')
def user_logout(request):
    logout(request)
    messages.success(request, "You have successfully logged out.")
    return redirect('login')

def forgot_password(request):
    dynamic_title = "Forgot Password"
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            
            try:
                user = User.objects.get(email=email)
            except ObjectDoesNotExist:
                messages.error(request, 'This email address is not associated with any account. Please try again.')
                return render(request, 'expenses/forgot_password.html', {'form': form, 'dynamic_title': dynamic_title})

            # Generate a one-time use link for password reset
            current_site = get_current_site(request)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            # Send email for password reset
            mail_subject = 'Reset Your Password'
            message_html = render_to_string('expenses/password_reset_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': uid,
                'token': token,
            })
            text_message = strip_tags(message_html)  # Extract plain text version from HTML content

            # Create an EmailMultiAlternatives object
            email_message = EmailMultiAlternatives(mail_subject, text_message, to=[email])
            email_message.attach_alternative(message_html, "text/html")  # Attach HTML content

            email_message.send()

            messages.success(request, "An email has been sent with instructions to reset your password.")
            return redirect('login')
        else:
            messages.error(request, 'Invalid email. Please try again.')

    else:
        form = ForgotPasswordForm()

    return render(request, 'expenses/forgot_password.html', {'form': form, 'dynamic_title': dynamic_title})

class CustomPasswordResetView(auth_views.PasswordResetView):
    template_name = 'expenses/custom_password_reset_form.html'
    email_template_name = 'expenses/password_reset_email.html'
    subject_template_name = 'password_reset_subject.txt'
    success_url = reverse_lazy('custom_password_reset_done')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dynamic_title'] = "Reset Password"
        return context

class CustomPasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = 'expenses/custom_password_reset_done.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dynamic_title'] = "Password Reset Done"
        return context

class CustomPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'expenses/custom_password_reset_confirm.html'
    success_url = reverse_lazy('custom_password_reset_complete')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dynamic_title'] = "Confirm Password Reset"
        return context

class CustomPasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = 'expenses/custom_password_reset_complete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dynamic_title'] = "Password Reset Completed"
        return context

@login_required(login_url='login')
def home(request):
    dynamic_title = "Home"
    events = Event.objects.filter(user=request.user)
    events_with_member_count = []

    for event in events:
        expenses = Expense.objects.filter(event=event)
        total_expense_amount = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
        members = Member.objects.filter(event=event)
        member_count = members.count()
        # Calculate the difference in days
        date_difference = (event.end_date - event.start_date).days + 1
        events_with_member_count.append({
            'event': event,
            'member_count': member_count,
            'date_difference':date_difference,
            'total_expense_amount': total_expense_amount
        })

    return render(request, 'expenses/home.html', {'events': events_with_member_count, 'dynamic_title': dynamic_title})

@login_required(login_url='login')
def create_event(request):
    dynamic_title = "Create Event"
    if request.method == 'POST':
        event_form = EventForm(request.POST)
        if event_form.is_valid():
            event = event_form.save(commit=False)
            event.user = request.user
            event.save()

            messages.success(request, 'Event created successfully!')
            return redirect('event_details', event_id=event.id)

    else:
        event_form = EventForm()

    return render(request, 'expenses/create_event.html', {'event_form': event_form, 'dynamic_title':dynamic_title})

@login_required(login_url='login')
def handle_member_form(request, event):
    member_form = MemberForm(request.POST or None)
    
    if member_form.is_valid():
        member_name = member_form.cleaned_data['name']
        
        # Check if a member with the same name already exists in the event
        existing_member = Member.objects.filter(event=event, name=member_name).first()

        if existing_member:
            # Display an error message if the member with the same name already exists
            messages.warning(request, f'Member "{member_name}" already exists in the event.')
        else:
            # Save the new member if it doesn't already exist
            member = member_form.save(commit=False)
            member.event = event
            member.save()
            # Add success message
            messages.success(request, f'Member "{member_name}" added successfully.')
    elif request.method == 'POST':
        # Display an error message for invalid form submission
        messages.error(request, 'Invalid form submission. Please check the entered data.')

    return member_form

@login_required(login_url='login')
def handle_expense_form(request, event):
    expense_form = ExpenseForm(request.POST, request.FILES)
    error_message = None
    
    if request.method == 'POST':
        if expense_form.is_valid():
            # Save the new expense if the form is valid
            expense = expense_form.save(commit=False)
            # Set the user field to the currently logged-in user
            expense.user = request.user
            expense.event = event
            expense.payer = expense_form.cleaned_data['payer']
            contributors = expense_form.cleaned_data.get('contributors', [])
            expense.save()
            expense.contributors.set(contributors)
            
            # Add success message
            messages.success(request, f'Expense "{expense.description} (Paid by: {expense.payer})" added successfully.')
        else:
            # Set the error message for template rendering
            error_message = 'Invalid form submission. Please check the entered data.'
            messages.error(request, error_message)

    return expense_form, error_message

@login_required(login_url='login')
def event_details(request, event_id):
    event = get_object_or_404(Event, pk=event_id, user=request.user)
    dynamic_title = f"Event ({event.title})"
    member_form = MemberForm(request.POST or None)
    expense_form = ExpenseForm(request.POST or None, event=event)

    if request.method == 'POST':
        if 'add_member' in request.POST:
            handle_member_form(request, event)
            return redirect('event_details', event_id=event_id)
        elif 'add_expense' in request.POST:
            handle_expense_form(request, event)
            return redirect('event_details', event_id=event_id)

    members = Member.objects.filter(event=event)
    expenses = Expense.objects.filter(event=event)
    
    total_expense_amount = expenses.aggregate(Sum('amount'))['amount__sum'] or 0

    context = {
        'event': event,
        'members': members,
        'expenses': expenses,
        'member_form': member_form,
        'expense_form': expense_form,
        'total_expense_amount': total_expense_amount,
        'dynamic_title':dynamic_title
    }

    return render(request, 'expenses/event_details.html', context)


@login_required(login_url='login')
def add_member(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    error_message = None

    if request.method == 'POST':
        member_form = MemberForm(request.POST)
        if member_form.is_valid():
            member_name = member_form.cleaned_data['name']

            # Check if a member with the same name already exists in the event
            existing_member = Member.objects.filter(event=event, name=member_name).first()

            if existing_member:
                # Set the error message for template rendering
                error_message = f'Member "{member_name}" already exists in the event.'
                messages.warning(request, error_message)
            else:
                # Save the new member if it doesn't already exist
                member = member_form.save(commit=False)
                member.event = event
                # Set the user field to the currently logged-in user
                member.user = request.user
                member.save()

                # Add success message
                messages.success(request, f'Member "{member_name}" added successfully.')
                
        elif request.method == 'POST':
        # Display an error message for invalid form submission
            messages.error(request, 'Invalid form submission. Please check the entered data.')

    return redirect('event_details', event_id=event.id)

@login_required(login_url='login')
def members(request, event_id):
    event = get_object_or_404(Event, id=event_id, user=request.user)
    dynamic_title = f"Members ({event.title})"
    members = Member.objects.filter(event=event)
    # Calculate total expenses paid by each member
    for member in members:
        member.total_expenses_paid = Expense.objects.filter(event=event, payer=member).aggregate(Sum('amount'))['amount__sum'] or 0
    context = {
        'event': event,
        'members': members,
        'dynamic_title': dynamic_title,
    }

    return render(request, 'expenses/members.html', context)

@login_required(login_url='login')
def edit_member(request, event_id, member_id):
    event = get_object_or_404(Event, id=event_id, user=request.user)
    dynamic_title = f"Edit Members ({event.title})"
    member = get_object_or_404(Member, id=member_id, event=event)

    if request.method == 'POST':
        # Handle the form submission to update the member name
        new_name = request.POST.get('new_name')
        member.name = new_name
        member.save()
        messages.success(request, f'Member name "{member.name}" updated successfully.')
        # Optionally, add a success message or redirect to the members view
        return redirect('members', event_id=event.id)

    context = {'event': event, 'member': member, 'dynamic_title': dynamic_title,}
    return render(request, 'expenses/edit_member.html', context)

@login_required(login_url='login')
def delete_member(request, event_id, member_id):
    event = get_object_or_404(Event, id=event_id, user=request.user)
    member = get_object_or_404(Member, id=member_id, event=event)

    if request.method == 'POST':
        # Delete the member
        member.delete()
        messages.success(request, f'Member "{member.name}" deleted successfully.')
        return redirect('members', event_id=event.id)

    context = {'event': event, 'member': member}
    return render(request, 'expenses/members.html', context)

# def expense_list(request, event_id):
#     event = get_object_or_404(Event, pk=event_id)
#     dynamic_title = f"Expenses({event.title})"
#     expenses = Expense.objects.filter(event_id=event_id)
#     return render(request, 'expenses/expense_list.html', {'expenses': expenses, 'dynamic_title':dynamic_title, 'event':event})

@login_required(login_url='login')
def expense_detail(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id, user=request.user)
    event = expense.event
    dynamic_title = f"Expense Details ({expense.description})"

    # Get the contributors and their contributions for the specific expense
    contributors = expense.contributors.all()
    # Calculate the total contribution amount
    contributions_amount = expense.amount / contributors.count()

    context = {
        'event': event,
        'expense': expense,
        'contributions_amount': contributions_amount,
        'dynamic_title': dynamic_title
    }

    return render(request, 'expenses/expense_detail.html', context)

@login_required(login_url='login')
def edit_expense(request, expense_id):
    expense = Expense.objects.get(pk=expense_id, user=request.user)
    event = expense.event
    dynamic_title = f"Edit Expense ({event.title})"

    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense, event=event)
        if form.is_valid():
            form.save()
            messages.success(request, f'Expense "{expense.description}" updated successfully.')
            return redirect('expense_detail', expense_id=expense.id)
        else:
            messages.error(request, 'Invalid form submission. Please check the entered data.')
    else:
        form = ExpenseForm(instance=expense, event=event)

    return render(request, 'expenses/edit_expense.html', {'form': form, 'expense': expense, 'event': event, 'dynamic_title': dynamic_title})

@login_required(login_url='login')
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id, user=request.user)
    dynamic_title = f"Edit Event ({event.title})"

    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, f'Event "{event.title}" updated successfully.')
            return redirect('event_details', event_id=event.id)
        else:
            messages.error(request, 'Invalid form submission. Please check the entered data.')
    else:
        form = EventForm(instance=event)

    return render(request, 'expenses/edit_event.html', {'form': form, 'event': event, 'dynamic_title': dynamic_title})

@require_POST
@login_required(login_url='login')
def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, pk=expense_id, user=request.user)
    expense.delete()
    messages.success(request, f'Expense "{expense.description}" deleted successfully.')
    return redirect('expense_audit_trail', event_id=expense.event_id)

# Master Code
@login_required(login_url='login')
def generate_report(request, event_id):
    dynamic_title = "Financial Report"
    event = get_object_or_404(Event, id=event_id, user=request.user)
    # Check if the logged-in user is the owner of the event
    # if event.user != request.user:
    #     messages.error(request, "You do not have permission to view this report.")
    #     return redirect('home')
    date_difference = (event.end_date - event.start_date).days + 1
    
    # Get all members associated with the event
    members = Member.objects.filter(event=event)
    
    # Get all expenses associated with the event
    expenses = Expense.objects.filter(event=event)
    
    # Get the total sum of amount for all expenses in the event
    total_expense_amount = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Default values for the form
    selected_user_id = None
    user_report = None
    contributors = None
    selected_user = None
    selected_user_expenses = None
    other_user_expenses = None
    expense_count = None
    # Initialize the variable here
    balance = 0
    total_expenses_paid = 0
    total_contribution = 0
    total_expenses_paid_by_user = 0
    
    if request.method == 'POST':
        # Form is submitted, retrieve the selected member ID
        selected_user_id = request.POST.get('user_select')

        # Retrieve the user object based on the selected ID
        selected_user = get_object_or_404(Member, id=selected_user_id)
        dynamic_title = f"Financial Report ({selected_user})"

        # Get all contributors (excluding the selected user)
        contributors = Member.objects.filter(event=event).exclude(id=selected_user_id)
        
        # all_contributors = Member.objects.filter(event=event)
        # contributors_count = all_contributors.count()
        
        # Filter expenses where the selected user is the payer
        selected_user_expenses = Expense.objects.filter(event=event, payer=selected_user)
        
        # Calculate expenses count for the selected user
        expense_count = selected_user_expenses.count()
        
        # Calculate contribution amount for each expense
        for expense in selected_user_expenses:
            expense.contribution_amount = expense.amount / expense.contributors.count() if expense.contributors.count() > 0 else 0
            
        # Filter expenses where the other user is the payer
        other_user_expenses = Expense.objects.filter(event=event).exclude(payer=selected_user)
        
        # Calculate contribution amount for each expense
        for expense in other_user_expenses:
            expense.contribution_amount = expense.amount / expense.contributors.count() if expense.contributors.count() > 0 else 0
            

        # Calculate expenses paid, transactions received, and total balance for each contributor
        for contributor in contributors:
            # Get all expenses where the selected user is the payer
            expenses_paid_by_user = Expense.objects.filter(event=event, payer=selected_user, contributors=contributor)
            total_expenses_paid_by_user = expenses_paid_by_user.aggregate(Sum('amount'))['amount__sum'] or 0

            # Get all expenses where the contributor is the payer
            expenses_paid_to_contributor = Expense.objects.filter(event=event, payer=contributor, contributors=selected_user)
            total_expenses_paid_to_contributor = expenses_paid_to_contributor.aggregate(Sum('amount'))['amount__sum'] or 0

            # Calculate total contribution amount for the selected user
            total_contribution = total_expenses_paid_by_user

            # Calculate total expenses paid by the selected user
            total_expenses_paid = total_expenses_paid_by_user + total_expenses_paid_to_contributor

            # Calculate total balance for the contributor
            balance = total_expenses_paid_by_user - total_expenses_paid_to_contributor
            
            # Calculate expenses paid by the contributor
            contributor.expenses_paid = Expense.objects.filter(event=event, payer=contributor).aggregate(Sum('amount'))['amount__sum'] or 0
            
            # Calculate expenses count for the selected user
            expense_count = expenses_paid_by_user.count()

            # Add expense_count to the contributor dictionary
            contributor.expense_count = expense_count
            
            contributors_count = expense.contributors.count()

            # Calculate pay_to and get_from amounts for the contributor
            contributor.pay_to = max(0, -balance) / contributors_count # The amount the contributor needs to pay to others
            contributor.get_from = max(0, balance) / contributors_count # The amount the contributor can get from others
            
            # Calculate the percentage based on the total expense amount and the user's contribution
            # Calculate percentage_spent only if total_expense_amount is greater than zero
            percentage_spent = 0
            if total_expense_amount > 0:
                percentage_spent = (contributor.expenses_paid / total_expense_amount) * 100

            # Add the percentage_spent to the contributor object
            contributor.percentage_spent = percentage_spent
            
        # Default value for selected_user_percentage_spent
        selected_user_percentage_spent = 0

        # Calculate the percentage spent by the selected user
        if total_expense_amount > 0:
            selected_user_percentage_spent = (total_expenses_paid_by_user / total_expense_amount) * 100

        # Add the selected_user_percentage_spent to the selected_user object
        selected_user.percentage_spent = selected_user_percentage_spent

        # Create a dictionary with report details
        user_report = {
            'user_name': selected_user.name,
            'total_contribution': total_contribution,
            'total_expenses_paid': total_expenses_paid,
            'balance': balance,
            'expense_count': expense_count,
            'expenses_added': total_expenses_paid_by_user > 0,
        }

    context = {
        'event': event,
        'members': members,
        'selected_user_id': selected_user_id,
        'user_report': user_report,
        'contributors': contributors,
        'total_expense_amount': total_expense_amount,
        'selected_user': selected_user,
        'selected_user_expenses': selected_user_expenses,
        'other_user_expenses': other_user_expenses,
        'expense_count': expense_count,
        'date_difference': date_difference,
        'dynamic_title':dynamic_title,
    }
    
    return render(request, 'expenses/report.html', context)

def settlement(request, event_id):
    dynamic_title = "Settlement"
    event = get_object_or_404(Event, id=event_id, user=request.user)
    members = Member.objects.filter(event=event).count()
    expenses = Expense.objects.filter(event=event)
    total_expense_amount = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    
    each = 0
    member_percentile = 0
    if total_expense_amount > 0:
        each = total_expense_amount / members
        member_percentile = (each / total_expense_amount) * 100
    
    member_expenses = Expense.objects.filter(event=event)
    for expense in member_expenses:
        expense.contribution_amount = expense.amount / members if expense.contributors.count() > 0 else 0
    
    context = {
        'event': event,
        'dynamic_title': dynamic_title,
        'members': members,
        'each': each,
        'member_expenses': member_expenses,
        'member_percentile': member_percentile,
        'total_expense_amount': total_expense_amount,
    }
    
    return render(request, 'expenses/settlement.html', context)

@login_required(login_url='login')
def category_distribution_view(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    category_distribution = Expense.objects.filter(event=event).values('category').annotate(total_amount=Sum('amount'))

    total_expense_amount = Expense.objects.filter(event=event).aggregate(Sum('amount'))['amount__sum'] or 1
    category_distribution = category_distribution.annotate(percentile=ExpressionWrapper(F('total_amount') * 100.0 / total_expense_amount, output_field=fields.FloatField()))

    data = {
        'labels': [f"{item['category']} ({item['percentile']:.2f}%) - ₹{item['total_amount']:.2f}" for item in category_distribution],
        'data': [item['total_amount'] for item in category_distribution],
        'percentiles': [item['percentile'] for item in category_distribution],
    }

    return JsonResponse(data)

@login_required(login_url='login')
def selected_user_expense_view(request, event_id, user_id):
    event = get_object_or_404(Event, id=event_id)
    selected_user = get_object_or_404(Member, id=user_id)

    selected_user_expenses = Expense.objects.filter(event=event, payer=selected_user).values('category').annotate(total_amount=Sum('amount'))
    total_user_expense_amount = selected_user_expenses.aggregate(Sum('total_amount'))['total_amount__sum'] or 1
    selected_user_expenses = selected_user_expenses.annotate(percentile=ExpressionWrapper(F('total_amount') * 100.0 / total_user_expense_amount, output_field=fields.FloatField()))

    data = {
        'labels': [f"{item['category']} ({item['percentile']:.2f}%) - ₹{item['total_amount']:.2f}" for item in selected_user_expenses],
        'data': [item['total_amount'] for item in selected_user_expenses],
        'percentiles': [item['percentile'] for item in selected_user_expenses],
    }

    return JsonResponse(data)

@login_required(login_url='login')
def expense_audit_trail(request, event_id):
    event = get_object_or_404(Event, pk=event_id, user=request.user)
    dynamic_title = f"Audit Trail ({event.title})"
    expenses = Expense.objects.filter(event_id=event_id, user=request.user)
    
    # Create a list to store detailed information for each expense
    expense_details_list = []

    for expense in expenses:
        # Get the payer (user who paid the expense)
        payer = expense.payer

        # Get the contributors and their contributions for the specific expense
        contributors = expense.contributors.all()

        # Calculate the total contribution amount
        if contributors.count() > 0:
            total_contribution = expense.amount / contributors.count()
        else:
            total_contribution = 0  # Or handle this case according to your application logic


        # Create a list to store detailed information for each contributor
        contributor_details = []

        # Add details for the payer
        payer_detail = {
            'name': payer.name,
            'contribution': total_contribution,
            'paid_amount': expense.amount,
        }
        contributor_details.append(payer_detail)

        # Add details for other contributors
        for contributor in contributors:
            if contributor != payer:  # Skip the payer in contributor details
                contributor_detail = {
                    'name': contributor.name,
                    'contribution': total_contribution,
                }
                contributor_details.append(contributor_detail)

        # Combine contributor names into a comma-separated string
        contributor_names = ', '.join(detail['name'].split()[0] for detail in contributor_details)

        # Add the combined details to the expense_details_list
        expense_details_list.append({
            'expense': expense,
            'contributor_names': contributor_names,
            'total_contribution': total_contribution,
        })

    context = {
        'expense_details_list': expense_details_list,
        'dynamic_title': dynamic_title,
        'event': event,
    }

    return render(request, 'expenses/expense_audit_trail.html', context)

# def analytics(request):
#     event = Event.objects.filter(user=request.user)
#     dynamic_title = f"Analytics"

#     # Get the count of events created per year
#     events_by_year = event.annotate(year=ExtractYear('start_date')).values('year').annotate(count=Count('id'))

#     # Get the count of expenses paid for each event per month
#     expenses_by_month = Expense.objects.filter(event__in=event).annotate(
#         year=ExtractYear('event__start_date'),
#         month=ExtractMonth('event__start_date')
#     ).values('year', 'month').annotate(count=Count('id'))

#     # Convert queryset to list for serialization
#     events_by_year_list = list(events_by_year)
#     expenses_by_month_list = list(expenses_by_month)
    
#     context = {
#         'events_by_year': events_by_year_list,
#         'expenses_by_month': expenses_by_month_list,
#         'dynamic_title': dynamic_title,
#     }
#     return render(request, 'expenses/analytics.html', context)

def analytics(request):
    user = request.user
    events = Event.objects.filter(user=user)
    expenses = Expense.objects.filter(event__in=events)
    
    # Total number of events
    total_events = events.count()

    # Total events expenditure
    total_event_expenditure = events.aggregate(total_expenditure=Sum('expense__amount'))['total_expenditure'] or 0

    # Total expenses count
    total_expenses_count = expenses.count()

    # Get the count of events created per year
    events_by_year = events.annotate(year=ExtractYear('start_date')).values('year').annotate(count=Count('id'))

    # Get the count of expenses paid for each event per month
    expenses_by_month = expenses.annotate(
        year=ExtractYear('event__start_date'),
        month=ExtractMonth('event__start_date')
    ).values('year', 'month').annotate(count=Count('id'))

    context = {
        'total_events': total_events,
        'total_event_expenditure': total_event_expenditure,
        'total_expenses_count': total_expenses_count,
        'events_by_year': events_by_year,
        'expenses_by_month': expenses_by_month,
        'dynamic_title': "Analytics",
    }
    return render(request, 'expenses/analytics.html', context)

def expense_and_event_by_month_and_day(request):
    # Fetch events created by month and day date
    events_by_month_and_day = Event.objects.filter(user=request.user).annotate(
        year=ExtractYear('start_date'),  # Add year annotation
        month=ExtractMonth('start_date'),
        day=ExtractDay('start_date')
    ).values('year', 'month', 'day').annotate(event_count=Count('id')).order_by('year', 'month', 'day')

    # Fetch expenses by month and day date within the event start and end dates
    expenses_by_month_and_day = Expense.objects.filter(
        event__user=request.user,
        event__start_date__lte=F('date'),  # Expense date should be after or equal to event start date
        event__end_date__gte=F('date')     # Expense date should be before or equal to event end date
    ).annotate(
        year=ExtractYear('date'),  # Add year annotation
        month=ExtractMonth('date'),
        day=ExtractDay('date')
    ).values('year', 'month', 'day').annotate(expense_count=Count('id')).order_by('year', 'month', 'day')

    # Combine the data for expenses and events into a single dictionary
    data = {
        'events': list(events_by_month_and_day),
        'expenses': list(expenses_by_month_and_day)
    }

    return JsonResponse(data, safe=False)


def analytics_data_by_month(request):
    user_events = Event.objects.filter(user=request.user)

    # Get the count of events created per year
    events_by_year = user_events.annotate(year=ExtractYear('start_date')).values('year').annotate(count=Count('id'))

    # Get the count of expenses paid for each event per month
    expenses_by_month = Expense.objects.filter(event__in=user_events).annotate(
        year=ExtractYear('event__start_date'),
        month=ExtractMonth('event__start_date')
    ).values('year', 'month').annotate(count=Count('id'))

    # Manually create month names and corresponding expense counts for the line chart
    line_chart_labels = []
    line_chart_data = []

    month_names = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]

    for entry in expenses_by_month:
        month_name = month_names[entry['month'] - 1]  # Adjust month index
        line_chart_labels.append(f"{entry['year']}-{month_name}")
        line_chart_data.append(entry['count'])

    # Convert the queryset data to a dictionary
    data = {
        'events_by_year': list(events_by_year),
        'expenses_by_month': list(expenses_by_month),
        'line_chart_data': {
            'labels': line_chart_labels,
            'data': line_chart_data,
        },
    }

    return JsonResponse(data, safe=False)

def analytics_data_by_year(request):
    user_events = Event.objects.filter(user=request.user)

    # Get the count of events created per year
    events_by_year = user_events.annotate(year=ExtractYear('start_date')).values('year').annotate(count=Count('id'))

    # Convert the queryset data to a dictionary
    data = {
        'events_by_year': list(events_by_year),
        'bar_chart_data': {
            'labels': [entry['year'] for entry in events_by_year],
            'data': [entry['count'] for entry in events_by_year],
        }
    }

    return JsonResponse(data, safe=False)


def analytics_data(request):
    user_events = Event.objects.filter(user=request.user)

    # Get the count of events created per year
    events_by_year = user_events.annotate(year=ExtractYear('start_date')).values('year').annotate(count=Count('id'))

    # Get the count of expenses paid for each event per month
    expenses_by_month = Expense.objects.filter(event__in=user_events).annotate(
        year=ExtractYear('event__start_date'),
        month=ExtractMonth('event__start_date')
    ).values('year', 'month').annotate(count=Count('id'))

    # Calculate the total expense for each event per year
    event_expenditure_by_year = user_events.annotate(
        year=ExtractYear('start_date')
    ).values('year').annotate(
        total_expenditure=Sum('expense__amount')
    )

    # Manually create month names and corresponding expense counts for the line chart
    line_chart_labels = []
    line_chart_data = []

    month_names = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]

    for entry in expenses_by_month:
        month_name = month_names[entry['month'] - 1]  # Adjust month index
        line_chart_labels.append(f"{entry['year']}-{month_name}")
        line_chart_data.append(entry['count'])

    # Convert the queryset data to a dictionary
    data = {
        'events_by_year': list(events_by_year),
        'bar_chart_events_by_year': {
            'labels': [entry['year'] for entry in events_by_year],
            'data': [entry['count'] for entry in events_by_year],
        },
        'line_chart_expenses_by_month': {
            'labels': [entry['year'] for entry in expenses_by_month],
            'data': [entry['count'] or 0 for entry in expenses_by_month],
        },
        'event_expenditure_data': {
            'labels': [entry['year'] for entry in event_expenditure_by_year],
            'data': [entry['total_expenditure'] or 0 for entry in event_expenditure_by_year],
        }
    }

    return JsonResponse(data, safe=False)


def calculate_expense_by_category(user):
    expenses_by_category = Expense.objects.filter(user=user).values('category').annotate(total_amount=Sum('amount'))
    return {entry['category']: entry['total_amount'] for entry in expenses_by_category}

def expense_by_category(request):
    if request.method == 'GET':
        user = request.user
        expenses_by_category = calculate_expense_by_category(user)
        return JsonResponse(expenses_by_category)
    
def percentage_by_category(request):
    if request.method == 'GET':
        user = request.user
        expenses_by_category = Expense.objects.filter(user=user).values('category').annotate(total_amount=Sum('amount'))
        
        total_expenses = sum(entry['total_amount'] for entry in expenses_by_category)
        
        if total_expenses != 0:
            percentages = {entry['category']: round((entry['total_amount'] / total_expenses) * 100, 2) for entry in expenses_by_category}
        else:
            percentages = {}
    
        return JsonResponse(percentages)

def error_404_view(request, exception):
    dynamic_title = "Page Not Found"
    return render(request, '404.html', {'dynamic_title': dynamic_title}, status=404)

def error_500_view(request, exception=None):
    dynamic_title = "Internal Server Error"
    return render(request, '500.html', {'dynamic_title': dynamic_title}, status=500)

