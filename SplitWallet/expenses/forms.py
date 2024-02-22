from django import forms
from .models import Event, Member, Expense, Transaction

from django.contrib.auth.models import User  
from django.contrib.auth.forms import UserCreationForm  
from django.core.exceptions import ValidationError 


class CustomUserCreationForm(UserCreationForm):
    username = forms.CharField(label='username', min_length=5, max_length=150)  
    email = forms.EmailField(label='email')  
    password1 = forms.CharField(label='password', widget=forms.PasswordInput)  
    password2 = forms.CharField(label='Confirm password', widget=forms.PasswordInput) 
  
    def username_clean(self):  
        username = self.cleaned_data['username'].lower()  
        new = User.objects.filter(username = username)  
        if new.count():  
            raise ValidationError("User Already Exist")  
        return username  
  
    def email_clean(self):  
        email = self.cleaned_data['email'].lower()  
        new = User.objects.filter(email=email)  
        if new.count():  
            raise ValidationError(" Email Already Exist")  
        return email  
  
    def clean_password2(self):  
        password1 = self.cleaned_data['password1']  
        password2 = self.cleaned_data['password2']  
  
        if password1 and password2 and password1 != password2:  
            raise ValidationError("Password don't match")  
        return password2  
  
    def save(self, commit = True):  
        user = User.objects.create_user(  
            self.cleaned_data['username'],  
            self.cleaned_data['email'],  
            self.cleaned_data['password1']  
        )  
        return user
       
class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'start_date', 'end_date', 'location']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
        
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date:
            if end_date < start_date:
                raise ValidationError("End date must be greater than or equal to the start date.")

            if end_date == start_date and self.instance.pk is None:
                raise ValidationError("Events for the same start and end date should span at least a day.")

        return cleaned_data
        
class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(label='Email')

class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['name']

class ExpenseForm(forms.ModelForm):
    contributors = forms.ModelMultipleChoiceField(
        queryset=Member.objects.all(),
        widget=forms.CheckboxSelectMultiple,
    )
      
    class Meta:
        model = Expense
        fields = ['description', 'date', 'amount', 'payer', 'contributors', 'notes', 'document', 'category', 'payment_method', 'currency', 'approval_status', 'location']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'contributors': forms.CheckboxSelectMultiple,
        }
        
    def __init__(self, *args, **kwargs):
        event = kwargs.pop('event', None)
        super().__init__(*args, **kwargs)

        # Dynamically set the choices for the 'payer' field
        if event:
            members_for_event = Member.objects.filter(event=event)
            self.fields['payer'].queryset = members_for_event
            self.fields['contributors'].queryset = members_for_event
            
            # Automatically select all contributors
            self.initial['contributors'] = members_for_event.values_list('id', flat=True)

            
    def clean_date(self):
        date = self.cleaned_data['date']
        # event = self.cleaned_data.get('event') or self.instance.event
        event = getattr(self.instance, 'event', None)

        if event and (date < event.start_date or date > event.end_date):
            raise forms.ValidationError('Date must be within the event start and end dates.')

        return date

    def clean_contributors(self):
        # Ensure that contributors are only from the specified event
        contributors = self.cleaned_data['contributors']
        event = self.cleaned_data.get('event')
        if event:
            contributors = contributors.filter(event=event)
        return contributors

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['event', 'payer', 'payee', 'amount', 'expense']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Dynamically set the choices for the 'payer' and 'payee' fields
        event_members = self.instance.event.members.all()
        self.fields['payer'].queryset = event_members
        self.fields['payee'].queryset = event_members

        # Dynamically set the choices for the 'expense' field
        event_expenses = Expense.objects.filter(event=self.instance.event)
        self.fields['expense'].queryset = event_expenses