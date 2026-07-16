from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse


class Trip(models.Model):
    CURRENCY_CHOICES = [
        ('INR', 'Indian Rupee (₹)'),
        ('USD', 'US Dollar ($)'),
        ('EUR', 'Euro (€)'),
        ('GBP', 'British Pound (£)'),
        ('AED', 'UAE Dirham (د.إ)'),
        ('AUD', 'Australian Dollar (A$)'),
        ('CAD', 'Canadian Dollar (C$)'),
        ('SGD', 'Singapore Dollar (S$)'),
        ('JPY', 'Japanese Yen (¥)'),
        ('THB', 'Thai Baht (฿)'),
    ]
    CURRENCY_SYMBOLS = {
        'INR': '₹', 'USD': '$', 'EUR': '€', 'GBP': '£', 'AED': 'د.إ',
        'AUD': 'A$', 'CAD': 'C$', 'SGD': 'S$', 'JPY': '¥', 'THB': '฿',
    }

    name = models.CharField(max_length=120)
    destination = models.CharField(max_length=120, blank=True)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='INR')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trips')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('trip_detail', args=[self.pk])

    @property
    def total_expense(self):
        return self.expenses.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

    @property
    def member_count(self):
        return self.members.count()

    @property
    def currency_symbol(self):
        return self.CURRENCY_SYMBOLS.get(self.currency, self.currency)

    @property
    def per_person_share(self):
        count = self.member_count
        if count == 0:
            return Decimal('0.00')
        return (self.total_expense / count).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def member_share(self, member):
        count = self.member_count
        if count == 0 or member.trip_id != self.pk:
            return Decimal('0.00')

        total_cents = int((self.total_expense * 100).quantize(Decimal('1')))
        base_cents = total_cents // count
        remainder = total_cents % count

        ordered_members = list(self.members.all())
        try:
            position = ordered_members.index(member)
        except ValueError:
            return self.per_person_share

        cents = base_cents + (1 if position < remainder else 0)
        return (Decimal(cents) / Decimal('100')).quantize(Decimal('0.01'))


class Member(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='members')
    name = models.CharField(max_length=100)
    # Optional link to a real user account (e.g. the trip creator themselves)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='memberships')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['joined_at']
        unique_together = ('trip', 'name')

    def __str__(self):
        return f"{self.name} ({self.trip.name})"

    @property
    def total_paid(self):
        return self.expenses_paid.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

    @property
    def fair_share(self):
        return self.trip.member_share(self)

    @property
    def raw_balance(self):
        """Positive => this member is owed money. Negative => this member owes money."""
        return (self.total_paid - self.fair_share).quantize(Decimal('0.01'))

    @property
    def settled_out(self):
        return self.settlements_paid.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

    @property
    def settled_in(self):
        return self.settlements_received.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

    @property
    def adjusted_balance(self):
        """Balance after accounting for recorded settlements already paid."""
        return (self.raw_balance + self.settled_out - self.settled_in).quantize(Decimal('0.01'))


class Expense(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='expenses')
    title = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_by = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='expenses_paid')
    date = models.DateField()
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.title} - {self.trip.currency_symbol}{self.amount}"


class Settlement(models.Model):
    """A recorded (confirmed) payment made between two members to settle a debt."""
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='settlements')
    from_member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='settlements_paid')
    to_member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='settlements_received')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    settled_on = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ['-settled_on']

    def __str__(self):
        return f"{self.from_member.name} paid {self.to_member.name} {self.trip.currency_symbol}{self.amount}"
