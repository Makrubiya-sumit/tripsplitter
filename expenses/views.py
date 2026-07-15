from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView

from .forms import RegisterForm, TripForm, MemberForm, ExpenseForm, SettlementForm
from .models import Trip, Member, Expense, Settlement
from .utils import build_trip_workbook, simplify_settlements


class CustomLoginView(LoginView):
    template_name = 'registration/login.html'


class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = 'registration/register.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, f"Welcome, {self.object.username}! Your account was created.")
        return response

    def get_success_url(self):
        return reverse('dashboard')


def _get_owned_trip_or_404(user, pk):
    """Fetch a trip owned by the current user, or 404."""
    return get_object_or_404(Trip, pk=pk, created_by=user)


@login_required
def dashboard(request):
    trips = Trip.objects.filter(created_by=request.user)
    total_trips = trips.count()
    total_members = Member.objects.filter(trip__in=trips).count()
    total_expenses = Expense.objects.filter(trip__in=trips).aggregate(total=Sum('amount'))['total'] or 0
    recent_trips = trips[:5]
    context = {
        'total_trips': total_trips,
        'total_members': total_members,
        'total_expenses': total_expenses,
        'recent_trips': recent_trips,
    }
    return render(request, 'expenses/dashboard.html', context)


@login_required
def trip_list(request):
    trips = Trip.objects.filter(created_by=request.user)
    return render(request, 'expenses/trip_list.html', {'trips': trips})


@login_required
def trip_create(request):
    if request.method == 'POST':
        form = TripForm(request.POST)
        if form.is_valid():
            trip = form.save(commit=False)
            trip.created_by = request.user
            trip.save()
            messages.success(request, f"Trip '{trip.name}' created! Now add some members.")
            return redirect('trip_detail', pk=trip.pk)
    else:
        form = TripForm()
    return render(request, 'expenses/trip_create.html', {'form': form})


@login_required
def trip_detail(request, pk):
    trip = _get_owned_trip_or_404(request.user, pk)
    tab = request.GET.get('tab', 'members')

    member_form = MemberForm()
    expense_form = ExpenseForm(trip=trip)

    members = trip.members.all()
    settlement_suggestions = simplify_settlements(members) if tab == 'summary' else []

    context = {
        'trip': trip,
        'tab': tab,
        'members': members,
        'expenses': trip.expenses.select_related('paid_by'),
        'member_form': member_form,
        'expense_form': expense_form,
        'settlement_suggestions': settlement_suggestions,
        'recorded_settlements': trip.settlements.select_related('from_member', 'to_member'),
    }
    return render(request, 'expenses/trip_detail.html', context)


@login_required
def member_add(request, pk):
    trip = _get_owned_trip_or_404(request.user, pk)
    if request.method == 'POST':
        form = MemberForm(request.POST)
        if form.is_valid():
            member = form.save(commit=False)
            member.trip = trip
            member.save()
            messages.success(request, f"{member.name} added to the trip.")
        else:
            messages.error(request, "Could not add member (maybe that name is already used in this trip).")
    return redirect(f"{reverse('trip_detail', args=[trip.pk])}?tab=members")


@login_required
def member_remove(request, pk, member_id):
    trip = _get_owned_trip_or_404(request.user, pk)
    member = get_object_or_404(Member, pk=member_id, trip=trip)
    if request.method == 'POST':
        member.delete()
        messages.success(request, f"{member.name} removed from the trip.")
    return redirect(f"{reverse('trip_detail', args=[trip.pk])}?tab=members")


@login_required
def expense_add(request, pk):
    trip = _get_owned_trip_or_404(request.user, pk)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, trip=trip)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.trip = trip
            expense.save()
            messages.success(request, f"Expense '{expense.title}' added.")
        else:
            messages.error(request, "Please fix the errors below.")
    return redirect(f"{reverse('trip_detail', args=[trip.pk])}?tab=expenses")


@login_required
def expense_edit(request, pk, expense_id):
    trip = _get_owned_trip_or_404(request.user, pk)
    expense = get_object_or_404(Expense, pk=expense_id, trip=trip)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense, trip=trip)
        if form.is_valid():
            form.save()
            messages.success(request, "Expense updated.")
            return redirect(f"{reverse('trip_detail', args=[trip.pk])}?tab=expenses")
    else:
        form = ExpenseForm(instance=expense, trip=trip)
    return render(request, 'expenses/expense_edit.html', {'form': form, 'trip': trip, 'expense': expense})


@login_required
def expense_delete(request, pk, expense_id):
    trip = _get_owned_trip_or_404(request.user, pk)
    expense = get_object_or_404(Expense, pk=expense_id, trip=trip)
    if request.method == 'POST':
        expense.delete()
        messages.success(request, "Expense deleted.")
    return redirect(f"{reverse('trip_detail', args=[trip.pk])}?tab=expenses")


@login_required
def trip_expenses_export(request, pk):
    """Download this trip's expenses and totals as an Excel workbook."""
    trip = _get_owned_trip_or_404(request.user, pk)
    expenses = trip.expenses.select_related('paid_by')
    filename = ''.join(char if char.isalnum() or char in (' ', '-', '_') else '' for char in trip.name)
    filename = (filename.strip().replace(' ', '-') or 'trip-expenses')[:80]

    response = HttpResponse(
        build_trip_workbook(trip, expenses),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}-expenses.xlsx"'
    return response


@login_required
def settlement_record(request, pk):
    """Mark a suggested settlement as actually paid (or record a custom one)."""
    trip = _get_owned_trip_or_404(request.user, pk)
    if request.method == 'POST':
        form = SettlementForm(request.POST, trip=trip)
        if form.is_valid():
            settlement = form.save(commit=False)
            settlement.trip = trip
            settlement.save()
            messages.success(
                request,
                f"Recorded: {settlement.from_member.name} paid {settlement.to_member.name} "
                f"₹{settlement.amount}."
            )
        else:
            messages.error(request, "Could not record settlement.")
    return redirect(f"{reverse('trip_detail', args=[trip.pk])}?tab=summary")


@login_required
def trip_delete(request, pk):
    trip = _get_owned_trip_or_404(request.user, pk)
    if request.method == 'POST':
        name = trip.name
        trip.delete()
        messages.success(request, f"Trip '{name}' and all of its data were deleted.")
        return redirect('trip_list')
    return redirect('trip_detail', pk=trip.pk)
