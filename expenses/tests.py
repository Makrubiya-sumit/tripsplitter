from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from .models import Expense, Member, Trip


class ExpenseCalculationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='secret123')
        self.trip = Trip.objects.create(name='Test Trip', created_by=self.user)
        self.alice = Member.objects.create(trip=self.trip, name='Alice')
        self.bob = Member.objects.create(trip=self.trip, name='Bob')
        self.charlie = Member.objects.create(trip=self.trip, name='Charlie')

    def test_balanced_rounding_for_equal_split(self):
        Expense.objects.create(
            trip=self.trip,
            title='Dinner',
            amount=Decimal('100.00'),
            paid_by=self.alice,
            date='2026-01-01',
        )

        shares = [self.trip.member_share(member) for member in self.trip.members.all()]
        self.assertEqual(shares, [Decimal('33.34'), Decimal('33.33'), Decimal('33.33')])
        self.assertEqual(sum(shares, Decimal('0.00')), Decimal('100.00'))
        self.assertEqual(self.trip.member_share(self.alice), Decimal('33.34'))
        self.assertEqual(self.trip.member_share(self.bob), Decimal('33.33'))
        self.assertEqual(self.trip.member_share(self.charlie), Decimal('33.33'))
