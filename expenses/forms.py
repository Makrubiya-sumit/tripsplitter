from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Trip, Member, Expense, Settlement


class BootstrapFormMixin:
    """Adds Bootstrap's 'form-control' / 'form-select' classes to every field automatically."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get('class', '')
            css_class = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            field.widget.attrs['class'] = f"{existing} {css_class}".strip()


class RegisterForm(BootstrapFormMixin, UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class TripForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Trip
        fields = ['name', 'destination', 'currency', 'start_date', 'end_date']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g. Goa Trip'}),
            'destination': forms.TextInput(attrs={'placeholder': 'e.g. Goa, India'}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }


class MemberForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Member
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Member name'}),
        }


class ExpenseForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['title', 'amount', 'paid_by', 'date', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g. Hotel Booking'}),
            'amount': forms.NumberInput(attrs={'step': '0.01', 'placeholder': '0.00'}),
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.TextInput(attrs={'placeholder': 'Optional note'}),
        }

    def __init__(self, *args, trip=None, **kwargs):
        super().__init__(*args, **kwargs)
        if trip is not None:
            self.fields['paid_by'].queryset = trip.members.all()


class SettlementForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Settlement
        fields = ['from_member', 'to_member', 'amount']

    def __init__(self, *args, trip=None, **kwargs):
        super().__init__(*args, **kwargs)
        if trip is not None:
            self.fields['from_member'].queryset = trip.members.all()
            self.fields['to_member'].queryset = trip.members.all()
