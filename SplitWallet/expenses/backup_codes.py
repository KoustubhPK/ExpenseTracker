# Generating report issue with this code

@login_required(login_url='login')
def generate_report(request, event_id):
    dynamic_title = "Financial Report"
    event = get_object_or_404(Event, id=event_id, user=request.user)
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
        selected_user_id = request.POST.get('user_select')
        selected_user = get_object_or_404(Member, id=selected_user_id)
        dynamic_title = f"Financial Report ({selected_user})"
        contributors = Member.objects.filter(event=event).exclude(id=selected_user_id)
        all_contributors = Member.objects.filter(event=event)
        contributors_count = all_contributors.count()
        
        # Initialize the pay_get_dict with all contributor ids
        pay_get_dict = {contributor.id: {'pay_to': 0, 'get_from': 0} for contributor in contributors}
        
        # Check if there are any expenses
        if expenses.exists():
            # Initialize the pay_get_dict with all contributor ids and their pay_to/get_from values
            pay_get_dict = {contributor.id: {'pay_to': 0, 'get_from': 0} for contributor in contributors}

            # Inside the loop where you calculate pay_to and get_from
            for expense in expenses:
                # Calculate contribution amount for each expense
                expense.contribution_amount = expense.amount / expense.contributors.count() if expense.contributors.count() > 0 else 0

                # Calculate pay_to and get_from amounts for each contributor in this expense
                for contributor in expense.contributors.all():
                    # Ensure that the contributor.id is present in the dictionary
                    if contributor.id not in pay_get_dict:
                        pay_get_dict[contributor.id] = {'pay_to': 0, 'get_from': 0}

                    # Check if the contributor is the payer in this expense
                    if contributor == expense.payer:
                        # For the payer, the entire contribution amount is in get_from
                        pay_get_dict[contributor.id]['get_from'] += expense.contribution_amount
                    else:
                        # For other contributors, divide the contribution amount based on their count
                        pay_get_dict[contributor.id]['pay_to'] += max(0, -expense.contribution_amount)
                        # Only add to get_from if the contributor is associated with this expense
                        if contributor != expense.payer and contributor in expense.contributors.all():
                            pay_get_dict[contributor.id]['get_from'] += max(0, expense.contribution_amount)

        else:
            # Handle the case where there are no expenses
            # You can set default values or take appropriate action
            pass

        selected_user_expenses = Expense.objects.filter(event=event, payer=selected_user)
        expense_count = selected_user_expenses.count()

        for expense in selected_user_expenses:
            expense.contribution_amount = expense.amount / expense.contributors.count() if expense.contributors.count() > 0 else 0

        other_user_expenses = Expense.objects.filter(event=event).exclude(payer=selected_user)

        for expense in other_user_expenses:
            expense.contribution_amount = expense.amount / expense.contributors.count() if expense.contributors.count() > 0 else 0

        for contributor in contributors:
            expenses_paid_by_user = Expense.objects.filter(event=event, payer=selected_user, contributors=contributor)
            total_expenses_paid_by_user = expenses_paid_by_user.aggregate(Sum('amount'))['amount__sum'] or 0

            expenses_paid_to_contributor = Expense.objects.filter(event=event, payer=contributor, contributors=selected_user)
            total_expenses_paid_to_contributor = expenses_paid_to_contributor.aggregate(Sum('amount'))['amount__sum'] or 0

            total_contribution = total_expenses_paid_by_user
            total_expenses_paid = total_expenses_paid_by_user + total_expenses_paid_to_contributor
            balance = total_expenses_paid_by_user - total_expenses_paid_to_contributor

            contributor.expenses_paid = Expense.objects.filter(event=event, payer=contributor).aggregate(Sum('amount'))['amount__sum'] or 0
            expense_count = expenses_paid_by_user.count()
            contributor.expense_count = expense_count

            # Access pay_to and get_from values from the dictionary
            contributor.pay_to = pay_get_dict[contributor.id]['pay_to']
            contributor.get_from = pay_get_dict[contributor.id]['get_from']

            percentage_spent = 0
            if total_expense_amount > 0:
                percentage_spent = (contributor.expenses_paid / total_expense_amount) * 100

            contributor.percentage_spent = percentage_spent

        selected_user_percentage_spent = 0

        if total_expense_amount > 0:
            selected_user_percentage_spent = (total_expenses_paid_by_user / total_expense_amount) * 100

        selected_user.percentage_spent = selected_user_percentage_spent

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
        'dynamic_title': dynamic_title,
    }
    
    return render(request, 'expenses/report.html', context)