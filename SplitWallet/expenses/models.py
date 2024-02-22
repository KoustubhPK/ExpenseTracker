from django.db import models
from django.db.models import Case, When, Value, BooleanField, Sum
from django.contrib.auth.models import User


# Create your models here.

PAYMENT_METHOD_CHOICES = [
    ('cash', 'Cash'),
    ('credit_card', 'Credit Card'),
    ('debit_card', 'Debit Card'),
    ('online_payment', 'Online Payment'),
    ('other', 'Other'),
]

CATEGORY_CHOICES = [
    ('food', 'Food'),
    ('transportation', 'Transportation'),
    ('accommodation', 'Accommodation'),
    ('entertainment', 'Entertainment'),
    ('utilities', 'Utilities'),
    ('groceries', 'Groceries'),
    ('healthcare', 'Healthcare'),
    ('education', 'Education'),
    ('travel', 'Travel'),
    ('clothing', 'Clothing'),
    ('subscriptions', 'Subscriptions'),
    ('repairs', 'Repairs'),
    ('insurance', 'Insurance'),
    ('taxes', 'Taxes'),
    ('electronics', 'Electronics'),
    ('other', 'Other'),
]

class UserPreferences(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    dark_mode = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username + " Preferences"

class Event(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    location = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.title
    
    def all_expenses_approved(self):
        return self.expense_set.annotate(
            is_approved=Case(
                When(approval_status='Approved', then=Value(True)),
                default=Value(False),
                output_field=BooleanField()
            )
        ).aggregate(all_approved=Sum('is_approved'))['all_approved'] == self.expense_set.count()
        
    class Meta:
        ordering = ['-start_date']
    
class Member(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.name}"
    
class Expense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payer = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='payer')
    contributors = models.ManyToManyField(Member, related_name='contributed_expenses')
    notes = models.TextField(blank=True)
    document = models.FileField(upload_to='expense_documents/', blank=True, null=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, blank=True)
    currency = models.CharField(max_length=3, choices=[('INR', 'INR'), ('USD', 'USD'), ('EUR', 'EUR')], default='INR')
    location = models.CharField(max_length=50, blank=True)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, blank=True)
    approval_status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')], default='Pending')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    is_settled = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.payer.name} - {self.amount}"
    
    class Meta:
        ordering = ['-date']
    
class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    payer = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='payer_transaction')
    payee = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='payee_transaction')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.payer.name} to {self.payee.name} - {self.amount}"
