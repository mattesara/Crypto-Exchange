from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models
from django.conf import settings
from djongo.models.fields import ObjectIdField
from random import randint
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.FloatField(default=0)
    dollar_balance = models.FloatField(default=0)


class Order(models.Model):
    order_id = ObjectIdField()
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    datetime = models.DateTimeField(auto_now_add=True)
    price = models.FloatField()
    quantity = models.FloatField()
    remaining_quantity = models.FloatField(default=quantity)
    executed = models.BooleanField(default=False)
    BUY = 'BUY'
    SELL = 'SELL'
    TYPE_ORDER_CHOICES = [
        (BUY, 'Buy'),
        (SELL, 'Sell'),
    ]
    type_order = models.CharField(
        max_length=4,
        choices=TYPE_ORDER_CHOICES,
        default=BUY,
    )


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        instance.profile.balance = random.randint(1, 10)
        instance.profile.save()

class Transaction(models.Model):
    buyer = models.ForeignKey(Profile, related_name='buyer_transactions', on_delete=models.CASCADE)
    seller = models.ForeignKey(Profile, related_name='seller_transactions', on_delete=models.CASCADE)
    buy_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='buy_transactions')
    sell_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='sell_transactions')
    price = models.FloatField()
    quantity = models.FloatField()
    datetime = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.buy_order} -> {self.sell_order} ({self.quantity})'